"""Main application orchestrator."""

import asyncio
import logging
import signal
from typing import Any

from src.config import Config, build_parser
from src.logger_config import LoggerConfig
from src.attribute_filter import AttributeFilter
from src.device_manager import DeviceManager
from src.mqtt_bridge import MQTTBridge
from src.matter_client import MatterClient, AttributeUpdate
from src.command_handler import CommandRouter, MQTTCommand
from src.utils import safe_json

logger = logging.getLogger(__name__)


class MatterToMQTTApp:
    """Main application that bridges Matter and MQTT."""

    def __init__(self, config: Config):
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self.config = config
        self.device_manager = DeviceManager()
        self.attribute_filter = AttributeFilter.from_file(config.filter_file)
        self.matter_client = MatterClient(config.url_ws, config.reconnect_delay)
        self.command_router = CommandRouter(config.mqtt_topic_prefix)
        self.mqtt_bridge: MQTTBridge | None = None
        self.stop_event = asyncio.Event()
        self.event_loop: asyncio.AbstractEventLoop | None = None

    async def run(self) -> int:
        """Run the application.

        Returns:
            Exit code (0 for success, 1 for error)
        """
        # Store reference to event loop for use in callbacks
        self.event_loop = asyncio.get_running_loop()
        
        # Setup signal handlers
        loop = self.event_loop

        def _request_stop() -> None:
            self.stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                pass

        # Setup MQTT bridge (skip in dry-run mode)
        if not self.config.dry_run:
            logger.info("Connecting to MQTT broker at %s...", self.config.url_mqtt)
            try:
                self.mqtt_bridge = MQTTBridge(
                    self.config.url_mqtt,
                    username=self.config.mqtt_user,
                    password=self.config.mqtt_password,
                )
                self.mqtt_bridge.connect()
                logger.info("MQTT broker connected ✓")
                
                # Subscribe to command topics
                command_topic = f"{self.config.mqtt_topic_prefix}/+/+/+/command"
                simple_command_topic = f"{self.config.mqtt_topic_prefix}/+/+/command"
                self.mqtt_bridge.subscribe(command_topic, self._on_mqtt_message)
                self.mqtt_bridge.subscribe(simple_command_topic, self._on_mqtt_message)
                logger.info("Subscribed to command topics:")
                logger.info("  - %s", command_topic)
                logger.info("  - %s", simple_command_topic)
                
            except Exception as e:
                logger.error("Failed to connect to MQTT broker: %s", e)
                return 1
        else:
            logger.warning("Running in DRY RUN mode - no messages will be sent to MQTT")
        
        logger.info("Connecting to Matter server at %s...", self.config.url_ws)
        logger.info("Waiting for nodes list...")

        try:
            await self.matter_client.consume_messages(
                on_nodes_list=self._on_nodes_list,
                on_attribute_update=self._on_attribute_update,
                stop_event=self.stop_event,
            )
        finally:
            logger.info("")
            logger.info("Shutting down...")
            if self.mqtt_bridge is not None:
                self.mqtt_bridge.disconnect()
                logger.info("MQTT broker disconnected ✓")
            logger.info("="*60)
            logger.info("Matter-to-MQTT Bridge - Stopped")
            logger.info("="*60)

        return 0

    def _on_nodes_list(self, nodes: list[dict[str, Any]]) -> None:
        """Called when initial nodes list is received."""
        logger.info("")
        logger.info("★ Nodes list received with %d device(s) ★", len(nodes))
        self.device_manager.cache_node_identifiers(nodes)
        
        for node in nodes:
            node_id = node.get("node_id")
            identifier = self.device_manager.get_device_identifier(node_id)
            simple = self.device_manager.has_simple_endpoints(node_id)
            logger.info("  ✓ Node %s (device: %s, endpoints: %s)", 
                       node_id, identifier, "simple (0-1)" if simple else "complex")
        
        logger.info("Ready to process attributes")

    def _on_attribute_update(self, update: AttributeUpdate) -> None:
        """Called when an attribute is updated."""
        # Check if cluster 0 should be skipped
        if update.cluster_id == "0":
            logger.debug("Skipping cluster 0 attribute for node %s", update.node_id)
            return

        # Check if attribute is allowed by filter
        if not self.attribute_filter.is_allowed(update.cluster_id, update.attribute_id):
            logger.debug(
                "Attribute %s/%s filtered out (not in allowed list)",
                update.cluster_id,
                update.attribute_id,
            )
            return

        # Get device identifier
        device_id = self.device_manager.get_device_identifier(update.node_id)

        # Get cluster and attribute names
        cluster_name = self.attribute_filter.get_cluster_name(update.cluster_id) or update.cluster_id
        attribute_name = self.attribute_filter.get_attribute_name(
            update.cluster_id, update.attribute_id
        ) or update.attribute_id

        # Build topic
        has_simple_endpoints = self.device_manager.has_simple_endpoints(update.node_id)
        if has_simple_endpoints:
            topic = f"{self.config.mqtt_topic_prefix}/{device_id}/{cluster_name}/{attribute_name}"
        else:
            topic = f"{self.config.mqtt_topic_prefix}/{device_id}/{update.endpoint_id}/{cluster_name}/{attribute_name}"

        # Publish
        payload = safe_json(update.value)

        if self.config.dry_run or self.mqtt_bridge is None:
            logger.info("[DRY RUN] Would publish to %s: %s", topic, payload)
        else:
            self.mqtt_bridge.publish(topic, payload, qos=1, retain=False)

        logger.debug(
            "Attribute: device=%s, endpoint=%s, cluster=%s, attr=%s, value=%s, simple=%s",
            device_id,
            update.endpoint_id,
            update.cluster_id,
            update.attribute_id,
            update.value,
            has_simple_endpoints,
        )

    def _on_mqtt_message(self, topic: str, payload: str) -> None:
        """Called when MQTT message is received."""
        logger.debug("Received MQTT message on %s: %s", topic, payload)

        # Parse the command
        command = self.command_router.parse_mqtt_command(
            topic,
            payload,
            lambda device_id: self.device_manager.get_node_id_by_device_identifier(device_id),
        )

        if command is None:
            logger.debug("Could not parse command from topic=%s, payload=%s", topic, payload)
            return

        # Send the command to Matter
        self._send_command_to_device(command)

    def _send_command_to_device(self, command: MQTTCommand) -> None:
        """Send a command to a Matter device.

        Args:
            command: The MQTT command to send
        """
        if self.config.dry_run or self.mqtt_bridge is None:
            logger.info(
                "[DRY RUN] Would send command: node_id=%s, endpoint=%s, cluster=%s, command=%s",
                command.node_id,
                command.endpoint_id,
                command.cluster_id,
                command.command_name,
            )
            return

        # Schedule command on the event loop
        # Use run_coroutine_threadsafe() because this is called from MQTT callback (background thread)
        if self.event_loop is None:
            logger.error("Event loop not initialized")
            return
        
        try:
            asyncio.run_coroutine_threadsafe(
                self.matter_client.send_device_command(
                    command.node_id,
                    command.endpoint_id,
                    command.cluster_id,
                    command.command_name,
                    command.payload,
                ),
                self.event_loop
            )
        except Exception:
            pass


async def main_async(args) -> int:
    """Async main function."""
    # Setup logger (configures root logger for all modules)
    try:
        config = Config.from_yaml(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", flush=True)
        return 1
    
    LoggerConfig.setup(config.debug_level)

    logger.info("="*60)
    logger.info("Matter-to-MQTT Bridge - Starting up")
    logger.info("="*60)

    logger.info("Configuration loaded from: %s", args.config)
    logger.info("Configuration loaded")
    logger.info("  Matter WebSocket: %s", config.url_ws)
    logger.info("  MQTT Broker: %s", config.url_mqtt)
    logger.info("  MQTT Topic Prefix: %s", config.mqtt_topic_prefix)
    logger.info("  Attribute Filter: %s", config.filter_file)
    logger.info("  Reconnect Delay: %s seconds", config.reconnect_delay)
    logger.info("  Dry Run Mode: %s", config.dry_run)
    
    logger.info("Initializing application components...")
    app = MatterToMQTTApp(config)
    logger.info("Application components initialized ✓")
    logger.info("  Device Manager: ready")
    filter_count = len(app.attribute_filter.filter_data) if app.attribute_filter.filter_data else 0
    logger.info("  Attribute Filter: %d clusters configured", filter_count)
    logger.info("  Matter Client: ready")
    logger.info("  Command Router: ready")
    logger.info("")
    logger.info("Starting main event loop...")
    logger.info("")

    # Run app
    return await app.run()


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
