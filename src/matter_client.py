"""Matter WebSocket client and attribute parsing."""

import asyncio
import json
import logging
from typing import Any, Iterator

from websockets.exceptions import ConnectionClosed

try:
    from websockets import connect as ws_connect
except ImportError:
    from websockets.client import connect as ws_connect

from .utils import parse_path_fields, normalize_id

logger = logging.getLogger(__name__)


class AttributeUpdate:
    """Represents an attribute update from the Matter server."""

    def __init__(
        self,
        node_id: str,
        endpoint_id: str,
        cluster_id: str,
        attribute_id: str,
        value: Any,
    ):
        """Initialize attribute update."""
        self.node_id = node_id
        self.endpoint_id = endpoint_id
        self.cluster_id = normalize_id(cluster_id)
        self.attribute_id = normalize_id(attribute_id)
        self.value = value

    def __repr__(self) -> str:
        return (
            f"AttributeUpdate(node_id={self.node_id}, endpoint_id={self.endpoint_id}, "
            f"cluster_id={self.cluster_id}, attribute_id={self.attribute_id}, value={self.value})"
        )


class MatterClient:
    """WebSocket client for Matter server communication."""

    def __init__(self, ws_url: str, reconnect_delay: float = 5.0):
        """Initialize Matter client.

        Args:
            ws_url: WebSocket URL of the Matter server
            reconnect_delay: Seconds to wait between reconnection attempts
        """
        self.ws_url = ws_url
        self.reconnect_delay = reconnect_delay
        self._websocket: Any = None
        self._message_id_counter = 10  # Start from 10, lower IDs reserved

    @staticmethod
    def parse_attribute_update(message: dict[str, Any]) -> AttributeUpdate | None:
        """Parse an attribute_updated event.

        Returns AttributeUpdate or None if not an attribute_updated event or data is malformed.
        """
        event = str(message.get("event") or message.get("type") or "")
        data = message.get("data")

        if event != "attribute_updated":
            return None

        if not isinstance(data, list) or len(data) < 3:
            return None

        node_id = str(data[0])
        path_value = data[1]
        raw_value = data[2]
        endpoint_id, cluster_id, attribute_id, path_text = parse_path_fields(path_value)

        return AttributeUpdate(node_id, endpoint_id, cluster_id, attribute_id, raw_value)

    @staticmethod
    def iter_attribute_updates(message: dict[str, Any]) -> Iterator[AttributeUpdate]:
        """Yield attribute updates from a message."""
        update = MatterClient.parse_attribute_update(message)
        if update is not None:
            yield update

    async def consume_messages(
        self,
        on_nodes_list: callable,
        on_attribute_update: callable,
        stop_event: asyncio.Event,
    ) -> None:
        """Connect and consume messages from Matter server.

        Args:
            on_nodes_list: Callable(list[dict]) called with initial node list
            on_attribute_update: Callable(AttributeUpdate) called for each attribute update
            stop_event: Event to signal when to stop listening
        """
        while not stop_event.is_set():
            try:
                async with ws_connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=None,
                ) as websocket:
                    logger.info("Connected to %s", self.ws_url)
                    self.set_websocket(websocket)

                    # Request to start listening
                    await websocket.send(
                        json.dumps({"message_id": "3", "command": "start_listening"})
                    )

                    # Receive initial response with all commissioned nodes
                    await self._process_initial_nodes(websocket, on_nodes_list)

                    # Main event loop
                    await self._process_updates(websocket, on_attribute_update, stop_event)

            except (ConnectionClosed, OSError) as err:
                logger.warning("Connection lost: %s. Reconnecting in %s s...", err, self.reconnect_delay)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=self.reconnect_delay)
                except TimeoutError:
                    pass

    async def _process_initial_nodes(
        self,
        websocket: Any,
        on_nodes_list: callable,
    ) -> None:
        """Wait for and process the initial nodes list."""
        timeout_count = 0
        max_timeouts = 10

        while timeout_count < max_timeouts:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")

                logger.debug("Received message: %s", message[:500])

                try:
                    data = json.loads(message)

                    if isinstance(data, dict) and data.get("message_id") == "3":
                        logger.debug("Found message_id=3")
                        if "result" in data:
                            result = data["result"]
                            logger.debug("Found result, type: %s", type(result))

                            if isinstance(result, list):
                                logger.debug("Result is a list with %d item(s)", len(result))
                                on_nodes_list(result)
                                return
                            else:
                                logger.warning("Result is not a list, got %s", type(result))
                                return
                        else:
                            logger.warning("No 'result' key in message_id=3")
                            return
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse message: %s", e)

            except asyncio.TimeoutError:
                timeout_count += 1
                logger.warning("Timeout waiting for message_id=3 (%d/%d)", timeout_count, max_timeouts)

    async def _process_updates(
        self,
        websocket: Any,
        on_attribute_update: callable,
        stop_event: asyncio.Event,
    ) -> None:
        """Process attribute updates from WebSocket."""
        while not stop_event.is_set():
            recv_task = asyncio.create_task(websocket.recv())
            stop_task = asyncio.create_task(stop_event.wait())
            done, pending = await asyncio.wait(
                {recv_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if stop_task in done:
                if not recv_task.done():
                    recv_task.cancel()
                break

            raw_message = recv_task.result()
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode("utf-8", errors="replace")

            try:
                parsed = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            if not isinstance(parsed, dict):
                continue

            # Process attribute updates
            for update in self.iter_attribute_updates(parsed):
                on_attribute_update(update)

    async def send_device_command(
        self,
        node_id: str,
        endpoint_id: str,
        cluster_id: str,
        command_name: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Send a device command to the Matter server.

        Args:
            node_id: Matter node ID
            endpoint_id: Matter endpoint ID
            cluster_id: Matter cluster ID
            command_name: Command name (e.g., "On", "Off")
            payload: Command payload (default: empty dict)

        Returns:
            True if sent successfully, False otherwise
        """
        if self._websocket is None:
            logger.error("WebSocket not connected, cannot send command")
            return False

        if payload is None:
            payload = {}

        message_id = str(self._message_id_counter)
        self._message_id_counter += 1

        message = {
            "message_id": message_id,
            "command": "device_command",
            "args": {
                "node_id": int(node_id),
                "endpoint_id": int(endpoint_id),
                "cluster_id": int(cluster_id),
                "command_name": command_name,
                "payload": payload,
            },
        }

        try:
            await self._websocket.send(json.dumps(message))
            logger.info(
                "Sent command to device: node_id=%s, endpoint=%s, cluster=%s, command=%s",
                node_id,
                endpoint_id,
                cluster_id,
                command_name,
            )
            logger.debug("Command message: %s", message)
            return True
        except Exception as e:
            logger.error("Failed to send command: %s", e)
            return False

    def set_websocket(self, websocket: Any) -> None:
        """Store reference to active websocket for sending commands.

        This is called internally during consume_messages().

        Args:
            websocket: The connected websocket object
        """
        self._websocket = websocket
