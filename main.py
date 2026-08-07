"""Main application orchestrator."""

import asyncio
import logging
import signal
from typing import Any

from src.config import Config, build_parser
from src.logger_config import LoggerConfig
from src.attribute_filter import AttributeFilter
from src.device_manager import DeviceManager
from src.node_tracker import NodeTracker
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
        self.node_tracker = NodeTracker()
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
                
                # Register callback for when MQTT client connects
                self.mqtt_bridge.on_client_connect(self._on_mqtt_client_connect)
                
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
            # Create tasks for both message consumption and periodic polling
            consume_task = asyncio.create_task(
                self.matter_client.consume_messages(
                    on_nodes_list=self._on_nodes_list,
                    on_attribute_update=self._on_attribute_update,
                    stop_event=self.stop_event,
                )
            )
            
            poll_task = asyncio.create_task(
                self._poll_nodes_periodically()
            )

            # Wait for either task to complete (or stop_event)
            done, pending = await asyncio.wait(
                {consume_task, poll_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )

            # If one task completed with exception, stop the other
            for task in done:
                if task.done() and task.exception():
                    logger.error("Task failed: %s", task.exception())
                    self.stop_event.set()

            # Wait for all tasks to complete gracefully
            for task in pending:
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except asyncio.TimeoutError:
                    task.cancel()

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
        self.node_tracker.update_from_nodes_list(nodes)
        
        for node in nodes:
            node_id = node.get("node_id")
            identifier = self.device_manager.get_device_identifier(node_id)
            simple = self.device_manager.has_simple_endpoints(node_id)
            available = node.get("available", False)
            logger.info("  ✓ Node %s (device: %s, endpoints: %s, available: %s)", 
                       node_id, identifier, "simple (0-1)" if simple else "complex", available)
        
        logger.info("Ready to process attributes")
        
        # Publish node information after initial discovery
        self._publish_node_information()

    def _on_attribute_update(self, update: AttributeUpdate) -> None:
        """Called when an attribute is updated."""
        # Mark this node as having sent an update (update last_seen and availability)
        availability_changed = False
        try:
            node_id = int(update.node_id)
            availability_changed = self.node_tracker.mark_node_attribute_update(node_id)
            
            # Update signal metrics (WiFi RSSI, Thread device type, etc.)
            # Do this even if we skip publishing, to keep metrics current
            self.node_tracker.update_node_attribute(node_id, update.cluster_id, update.attribute_id, update.value)
        except (ValueError, TypeError):
            logger.debug("Could not parse node_id from attribute update: %s", update.node_id)
        
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

        # Always publish per-device availability and last_seen on attribute update
        try:
            node_id = int(update.node_id)
            self._publish_per_device_info(node_id)
        except (ValueError, TypeError):
            logger.debug("Could not parse node_id for per-device publishing: %s", update.node_id)

    async def _poll_nodes_periodically(self) -> None:
        """Periodically poll get_nodes command to update node availability."""
        logger.info(
            "Node polling enabled - will poll every %.1f seconds",
            self.config.nodes_poll_interval,
        )

        while not self.stop_event.is_set():
            try:
                # Wait for the interval or until stop_event is set
                await asyncio.wait_for(
                    self.stop_event.wait(),
                    timeout=self.config.nodes_poll_interval,
                )
                # If we get here, stop_event was set
                break
            except asyncio.TimeoutError:
                # Timeout expired, time to poll
                pass

            if self.stop_event.is_set():
                break

            try:
                # Request nodes list
                nodes = await self.matter_client.get_nodes()
                if nodes is not None:
                    # Update node tracker with fresh data
                    self.node_tracker.update_from_nodes_list(nodes)

                    # Log status summary
                    all_nodes = self.node_tracker.get_all_nodes()
                    available_nodes = self.node_tracker.get_available_nodes()
                    logger.info(
                        "Node status update: %d total, %d available",
                        len(all_nodes),
                        len(available_nodes),
                    )

                    # Publish updated node information to MQTT
                    self._publish_node_information()

                    # Log any nodes that became unavailable
                    for node in all_nodes:
                        if not node.available:
                            logger.debug(
                                "Node %d unavailable (last seen: %s)",
                                node.node_id,
                                node.last_seen.isoformat(),
                            )

            except Exception as e:
                logger.error("Error polling nodes: %s", e)

        logger.info("Node polling stopped")

    def _on_mqtt_client_connect(self) -> None:
        """Called when MQTT client connects (or reconnects)."""
        logger.info("MQTT client connected, publishing node information")
        self._publish_node_information()

    def _publish_per_device_info(self, node_id: int) -> None:
        """Publish per-device availability and last_seen for a single node.

        Args:
            node_id: The node ID to publish info for
        """
        if self.config.dry_run or self.mqtt_bridge is None:
            return

        try:
            node = self.node_tracker.get_node(node_id)
            if node is None:
                logger.debug("Node %d not found for per-device publishing", node_id)
                return

            # Publish availability state
            availability_topic = f"{self.config.mqtt_topic_prefix}/{node.unique_id}/availability"
            state = "online" if node.available else "offline"
            availability_payload = state

            self.mqtt_bridge.publish(
                availability_topic,
                availability_payload,
                qos=1,
                retain=True,
            )
            logger.debug(
                "Published availability for device %s (node %d): %s",
                node.unique_id,
                node.node_id,
                state,
            )

            # Publish last_seen timestamp
            last_seen_topic = f"{self.config.mqtt_topic_prefix}/{node.unique_id}/last_seen"
            self.mqtt_bridge.publish(
                last_seen_topic,
                node.last_seen.isoformat(),
                qos=1,
                retain=True,
            )
            logger.debug(
                "Published last_seen for device %s (node %d): %s",
                node.unique_id,
                node.node_id,
                node.last_seen.isoformat(),
            )

            # Also publish the nodes list to keep it in sync
            self._publish_nodes_list()

        except Exception as e:
            logger.error("Error publishing per-device info for node %d: %s", node_id, e)

    def _publish_nodes_list(self) -> None:
        """Publish the full nodes list to MQTT (debug logging)."""
        if self.config.dry_run or self.mqtt_bridge is None:
            return

        try:
            all_nodes = self.node_tracker.get_all_nodes()
            nodes_data = self.node_tracker.get_nodes_as_dicts()

            # Publish to nodes summary topic
            nodes_topic = f"{self.config.mqtt_topic_prefix}/nodes"
            nodes_payload = safe_json(nodes_data)
            self.mqtt_bridge.publish(
                nodes_topic,
                nodes_payload,
                qos=1,
                retain=True,
            )
            logger.debug("Published %d nodes to %s", len(all_nodes), nodes_topic)
            logger.debug("Nodes payload: %s", nodes_payload)

        except Exception as e:
            logger.error("Error publishing nodes list: %s", e)

    def _publish_node_information(self) -> None:
        """Publish current node information to MQTT (full nodes list + per-device info)."""
        if self.config.dry_run or self.mqtt_bridge is None:
            logger.info("[DRY RUN] Would publish node information to MQTT")
            return

        try:
            # Publish the nodes list
            all_nodes = self.node_tracker.get_all_nodes()
            self._publish_nodes_list()
            logger.info("Published %d nodes to MQTT", len(all_nodes))

            # Publish per-device info: availability, last_seen, RSSI, LQI
            for node in all_nodes:
                # Publish per-device availability and last_seen
                self._publish_per_device_info(node.node_id)
                
                # Publish RSSI value
                if node.wifi_rssi is not None or node.thread_rssi is not None:
                    rssi_topic = f"{self.config.mqtt_topic_prefix}/{node.unique_id}/rssi"
                    # Use WiFi RSSI if available, otherwise use Thread RSSI
                    rssi_value = node.wifi_rssi if node.wifi_rssi is not None else node.thread_rssi
                    self.mqtt_bridge.publish(
                        rssi_topic,
                        str(rssi_value),
                        qos=1,
                        retain=True,
                    )
                    logger.debug(
                        "Published RSSI for device %s (node %d): %s",
                        node.unique_id,
                        node.node_id,
                        rssi_value,
                    )

                # Publish LQI value
                if node.thread_lqi is not None:
                    lqi_topic = f"{self.config.mqtt_topic_prefix}/{node.unique_id}/lqi"
                    self.mqtt_bridge.publish(
                        lqi_topic,
                        str(node.thread_lqi),
                        qos=1,
                        retain=True,
                    )
                    logger.debug(
                        "Published LQI for device %s (node %d): %s",
                        node.unique_id,
                        node.node_id,
                        node.thread_lqi,
                    )

        except Exception as e:
            logger.error("Error publishing node information: %s", e)

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
