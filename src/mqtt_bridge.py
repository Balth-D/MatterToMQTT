"""MQTT client and bridge management."""

import logging
from urllib.parse import urlparse
from typing import Callable

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTBridge:
    """Manages MQTT client connection and message publishing."""

    def __init__(self, mqtt_url: str, username: str | None = None, password: str | None = None):
        """Initialize MQTT bridge.

        Args:
            mqtt_url: MQTT server URL (e.g., mqtt://localhost:1883)
            username: Optional MQTT username
            password: Optional MQTT password
        """
        parsed = urlparse(mqtt_url)
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 1883
        self.username = username
        self.password = password

        # Create client - handle both old and new paho-mqtt versions
        try:
            # Try new API (paho-mqtt >= 2.0.0)
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self._use_new_api = True
        except AttributeError:
            # Fall back to old API (paho-mqtt < 2.0.0)
            self.client = mqtt.Client(client_id="matter-to-mqtt")
            self._use_new_api = False
        
        self._is_connected = False
        self._on_message_callback: Callable[[str, str], None] | None = None
        self._on_client_connect_callback: Callable[[], None] | None = None
        self._subscribed_topics: set[str] = set()
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        """Setup MQTT client callbacks."""

        if self._use_new_api:
            # Callbacks for paho-mqtt >= 2.0.0 (VERSION2 API)
            def on_connect(client, userdata, connect_flags, reason_code, properties):
                if reason_code == 0:
                    logger.info("Connected to MQTT broker at %s:%s", self.host, self.port)
                    self._is_connected = True
                    
                    # Re-subscribe to topics on reconnect
                    # Create a copy to avoid "Set changed size during iteration" error
                    for topic in list(self._subscribed_topics):
                        client.subscribe(topic)
                        logger.debug("Re-subscribed to %s", topic)
                    
                    # Call client connect callback
                    if self._on_client_connect_callback:
                        try:
                            self._on_client_connect_callback()
                        except Exception as e:
                            logger.error("Error in client connect callback: %s", e)
                else:
                    logger.error("Failed to connect to MQTT broker: %s", reason_code)
                    self._is_connected = False

            def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
                if reason_code != 0:
                    logger.warning("Unexpected MQTT disconnection: %s", reason_code)
                else:
                    logger.info("Disconnected from MQTT broker")
                self._is_connected = False

            def on_publish(client, userdata, mid, reason_code, properties):
                if reason_code != 0:
                    logger.warning("MQTT publish failed: %s", reason_code)
        else:
            # Callbacks for paho-mqtt < 2.0.0 (old API)
            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    logger.info("Connected to MQTT broker at %s:%s", self.host, self.port)
                    self._is_connected = True
                    
                    # Re-subscribe to topics on reconnect
                    # Create a copy to avoid "Set changed size during iteration" error
                    for topic in list(self._subscribed_topics):
                        client.subscribe(topic)
                        logger.debug("Re-subscribed to %s", topic)
                    
                    # Call client connect callback
                    if self._on_client_connect_callback:
                        try:
                            self._on_client_connect_callback()
                        except Exception as e:
                            logger.error("Error in client connect callback: %s", e)
                else:
                    logger.error("Failed to connect to MQTT broker: %s", rc)
                    self._is_connected = False

            def on_disconnect(client, userdata, rc, properties=None):
                if rc != 0:
                    logger.warning("Unexpected MQTT disconnection: %s", rc)
                else:
                    logger.info("Disconnected from MQTT broker")
                self._is_connected = False

            def on_publish(client, userdata, mid, rc=None, properties=None):
                if rc is not None and rc != 0:
                    logger.warning("MQTT publish failed: %s", rc)

        def on_message(client, userdata, msg):
            if self._on_message_callback:
                try:
                    self._on_message_callback(msg.topic, msg.payload.decode("utf-8", errors="replace"))
                except Exception as e:
                    logger.error("Error in message callback: %s", e)

        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_publish = on_publish
        self.client.on_message = on_message

    def connect(self) -> None:
        """Connect to MQTT broker."""
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> None:
        """Publish a message to MQTT.

        Args:
            topic: MQTT topic
            payload: Message payload
            qos: Quality of service (0, 1, or 2)
            retain: Whether to retain the message
        """
        try:
            self.client.publish(topic, payload, qos=qos, retain=retain)
            logger.info("Published to %s: %s", topic, payload)
        except Exception as e:
            logger.error("Failed to publish to MQTT: %s", e)

    def subscribe(self, topic: str, on_message: Callable[[str, str], None]) -> None:
        """Subscribe to MQTT topic.

        Args:
            topic: Topic pattern (supports wildcards like +/*)
            on_message: Callback(topic, payload) when message received
        """
        self._subscribed_topics.add(topic)
        self._on_message_callback = on_message
        self.client.subscribe(topic)
        logger.info("Subscribed to topic: %s", topic)

    def on_client_connect(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when a client connects to MQTT.

        Args:
            callback: Callback function to call on client connection
        """
        self._on_client_connect_callback = callback
        logger.debug("Registered on_client_connect callback")

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from MQTT topic.

        Args:
            topic: Topic pattern to unsubscribe from
        """
        self._subscribed_topics.discard(topic)
        self.client.unsubscribe(topic)
        logger.info("Unsubscribed from topic: %s", topic)

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._is_connected
