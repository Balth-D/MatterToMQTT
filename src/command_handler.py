"""MQTT command handling and routing."""

import json
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MQTTCommand:
    """Represents a command received from MQTT."""

    def __init__(
        self,
        topic: str,
        node_id: str,
        endpoint_id: str,
        cluster_id: str,
        command_name: str,
        payload: dict[str, Any],
    ):
        """Initialize MQTT command.

        Args:
            topic: MQTT topic the command was received on
            node_id: Matter device node ID
            endpoint_id: Matter endpoint ID
            cluster_id: Matter cluster ID
            command_name: Command name (e.g., "On", "Off")
            payload: Command payload
        """
        self.topic = topic
        self.node_id = node_id
        self.endpoint_id = endpoint_id
        self.cluster_id = cluster_id
        self.command_name = command_name
        self.payload = payload

    def __repr__(self) -> str:
        return (
            f"MQTTCommand(node_id={self.node_id}, endpoint_id={self.endpoint_id}, "
            f"cluster_id={self.cluster_id}, command={self.command_name})"
        )


class CommandTopicParser:
    """Parses MQTT command topics and messages."""

    @staticmethod
    def parse_command_topic(
        topic: str, prefix: str
    ) -> tuple[str, str, str] | None:
        """Parse command topic to extract device_id, endpoint_id, cluster_id.

        Supports two formats:
        1. Full format: <prefix>/<device_id>/<endpoint_id>/<cluster_id>/command
        2. Simple format: <prefix>/<device_id>/<cluster_id>/command (endpoint defaults to 1)

        Args:
            topic: MQTT topic
            prefix: MQTT topic prefix (e.g., "matter")

        Returns:
            Tuple of (device_id, endpoint_id, cluster_id) or None if invalid format
        """
        parts = topic.split("/")

        # Check if topic ends with "command"
        if len(parts) < 3 or parts[-1] != "command":
            return None

        # Check if it starts with prefix
        if parts[0] != prefix:
            return None

        # Determine format based on number of parts
        # Format 1: prefix/device_id/endpoint_id/cluster_id/command (5 parts)
        # Format 2: prefix/device_id/cluster_id/command (4 parts, endpoint=1)
        
        if len(parts) == 5:
            # Full format with explicit endpoint
            device_id = parts[1]
            endpoint_id = parts[2]
            cluster_id = parts[3]
            
            # Validate that endpoint and cluster are numeric
            try:
                int(endpoint_id)
                int(cluster_id)
            except ValueError:
                logger.warning(
                    "Invalid command topic format: endpoint_id and cluster_id must be numeric: %s",
                    topic,
                )
                return None
            
            return device_id, endpoint_id, cluster_id
            
        elif len(parts) == 4:
            # Simple format without endpoint (defaults to endpoint 1)
            device_id = parts[1]
            cluster_id = parts[2]
            endpoint_id = "1"  # Default endpoint for simple devices
            
            # Validate that cluster is numeric
            try:
                int(cluster_id)
            except ValueError:
                logger.warning(
                    "Invalid command topic format: cluster_id must be numeric: %s",
                    topic,
                )
                return None
            
            logger.debug(
                "Parsed simple command topic (defaulting to endpoint 1): device=%s, cluster=%s",
                device_id,
                cluster_id,
            )
            return device_id, endpoint_id, cluster_id
        else:
            logger.warning(
                "Invalid command topic format: expected 4 or 5 parts, got %d: %s",
                len(parts),
                topic,
            )
            return None

    @staticmethod
    def parse_command_payload(payload: str) -> tuple[str, dict[str, Any]] | None:
        """Parse command payload.

        Expected format:
        {
            "command": "On",
            "payload": {}
        }

        Args:
            payload: MQTT payload string

        Returns:
            Tuple of (command_name, command_payload) or None if invalid
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse command payload as JSON: %s", e)
            return None

        if not isinstance(data, dict):
            logger.warning("Command payload must be a JSON object, got %s", type(data))
            return None

        command_name = str(data.get("command", "")).strip()
        command_payload = data.get("payload", {})

        if not command_name:
            logger.warning("Command payload missing 'command' field")
            return None

        if not isinstance(command_payload, dict):
            logger.warning("Command 'payload' must be an object, got %s", type(command_payload))
            return None

        return command_name, command_payload


class CommandRouter:
    """Routes MQTT commands to Matter devices."""

    def __init__(self, mqtt_topic_prefix: str):
        """Initialize command router.

        Args:
            mqtt_topic_prefix: MQTT topic prefix (e.g., "matter")
        """
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self._topic_parser = CommandTopicParser()

    def parse_mqtt_command(
        self, topic: str, payload: str, node_id_lookup: Callable[[str], str | None]
    ) -> MQTTCommand | None:
        """Parse MQTT topic and payload into a command.

        Args:
            topic: MQTT topic
            payload: MQTT payload string
            node_id_lookup: Callable(device_id) -> node_id or None

        Returns:
            MQTTCommand or None if invalid
        """
        # Parse topic
        parsed_topic = self._topic_parser.parse_command_topic(topic, self.mqtt_topic_prefix)
        if parsed_topic is None:
            logger.debug("Ignoring non-command topic: %s", topic)
            return None

        device_id, endpoint_id, cluster_id = parsed_topic

        # Look up node_id from device_id
        node_id = node_id_lookup(device_id)
        if node_id is None:
            logger.warning(
                "Unknown device ID: %s. Cannot route command from topic %s",
                device_id,
                topic,
            )
            return None

        # Parse payload
        parsed_payload = self._topic_parser.parse_command_payload(payload)
        if parsed_payload is None:
            return None

        command_name, command_payload = parsed_payload

        logger.debug(
            "Parsed command: node_id=%s, endpoint=%s, cluster=%s, command=%s",
            node_id,
            endpoint_id,
            cluster_id,
            command_name,
        )

        return MQTTCommand(
            topic=topic,
            node_id=node_id,
            endpoint_id=endpoint_id,
            cluster_id=cluster_id,
            command_name=command_name,
            payload=command_payload,
        )
