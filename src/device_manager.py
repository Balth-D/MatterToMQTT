"""Device management and identifier caching."""

import logging
from typing import Any
from re import match

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages device identifiers and endpoint tracking."""

    def __init__(self):
        """Initialize the device manager."""
        self._node_identifier_cache: dict[str, str] = {}
        self._devices_simple_endpoints: dict[str, bool] = {}

    def cache_node_identifiers(self, nodes_data: list[dict[str, Any]]) -> None:
        """Cache device identifiers from the initial nodes list.

        Expects a list of node objects, each containing:
        - node_id: The node ID
        - attributes: Dictionary with attribute paths and values

        Also tracks which devices only have endpoints 0 and 1.
        """
        for node in nodes_data:
            if not isinstance(node, dict):
                continue

            node_id = str(node.get("node_id"))
            attributes = node.get("attributes", {})

            if not isinstance(attributes, dict):
                continue

            # Look for the identifier attribute at 0/40/18
            identifier_value = attributes.get("0/40/18")
            # If we received something and this something is only alphanumeric, cache it
            if identifier_value is not None and node_id not in self._node_identifier_cache and bool(match("^[A-Za-z0-9]*$", str(identifier_value))):
                identifier = str(identifier_value).strip()
                identifier = "0x" + identifier.lower()
                if identifier:
                    self._node_identifier_cache[node_id] = identifier
                    logger.info("Cached identifier for node %s: %s", node_id, identifier)

            # Extract all endpoints from attribute paths to check if device is simple (only 0 and 1)
            endpoints = set()
            for path in attributes.keys():
                parts = str(path).split("/")
                if parts:
                    try:
                        endpoints.add(int(parts[0]))
                    except (ValueError, IndexError):
                        pass

            # Store whether this device only has endpoints 0 and 1
            simple_endpoints = endpoints <= {0, 1}  # subset check
            self._devices_simple_endpoints[node_id] = simple_endpoints
            if simple_endpoints:
                logger.debug("Device %s has only endpoints 0 and 1 (simple device)", node_id)

    def get_device_identifier(self, node_id: str) -> str:
        """Get the device identifier or fallback to node_id."""
        return self._node_identifier_cache.get(node_id, node_id)

    def has_simple_endpoints(self, node_id: str) -> bool:
        """Check if device only has endpoints 0 and 1."""
        return self._devices_simple_endpoints.get(node_id, False)

    def get_node_id_by_device_identifier(self, device_id: str) -> str | None:
        """Get node_id from device identifier (reverse lookup).

        Args:
            device_id: Device identifier

        Returns:
            node_id or None if not found
        """
        for node_id, cached_id in self._node_identifier_cache.items():
            if cached_id == device_id:
                return node_id
        return None

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._node_identifier_cache.clear()
        self._devices_simple_endpoints.clear()
