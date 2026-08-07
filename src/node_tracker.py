"""Node tracker for maintaining availability and state of Matter devices."""

import logging
from datetime import datetime
from re import match
from typing import Any, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class NodeInfo:
    """Information about a node in the Matter network."""

    def __init__(
        self,
        node_id: int,
        unique_id: str = None,
        available: bool = False,
        date_commissioned: Optional[str] = None,
        last_interview: Optional[str] = None,
    ):
        """Initialize node information.

        Args:
            node_id: The node ID in the Matter network
            unique_id: Unique identifier (typically from attribute 0/40/18)
            available: Whether the node is currently available
            date_commissioned: When the node was commissioned
            last_interview: When the node was last interviewed
        """
        self.node_id = node_id
        self.unique_id = unique_id
        self.available = available
        self.date_commissioned = date_commissioned
        self.last_interview = last_interview
        # Set last_seen based on availability: now if available, epoch if not
        self.last_seen = datetime.now() if available else datetime.fromtimestamp(0)
        # Matter over WiFi/Thread transport info
        self.device_type: Optional[str] = None  # "wifi" or "thread"
        self.wifi_rssi: Optional[int] = None  # WiFi RSSI in dBm
        self.thread_rssi: Optional[int] = None  # Thread RSSI in dBm
        self.thread_lqi: Optional[int] = None  # Thread LQI (0-255)
        self.thread_device_type: Optional[str] = None  # Thread device type

    def update_availability(self, available: bool) -> None:
        """Update the availability status and last_seen timestamp.

        Args:
            available: The new availability status
        """
        self.available = available
        # Update last_seen to now only if available
        if available:
            self.last_seen = datetime.now()
        else:
            # Set to epoch when unavailable
            self.last_seen = datetime.fromtimestamp(0)

    def update_last_seen(self) -> None:
        """Update the last_seen timestamp to now."""
        self.last_seen = datetime.now()

    def update_connectivity_info(self, device_type: Optional[str] = None,
                                  wifi_rssi: Optional[int] = None,
                                  thread_rssi: Optional[int] = None,
                                  thread_lqi: Optional[int] = None,
                                  thread_device_type: Optional[str] = None) -> None:
        """Update connectivity information.

        Args:
            device_type: "wifi" or "thread"
            wifi_rssi: WiFi RSSI in dBm
            thread_rssi: Thread RSSI in dBm
            thread_lqi: Thread LQI (0-255)
            thread_device_type: Thread device type description
        """
        updates = []
        if device_type is not None:
            if device_type != self.device_type:
                updates.append(f"device_type: {self.device_type} -> {device_type}")
            self.device_type = device_type
        if wifi_rssi is not None:
            if wifi_rssi != self.wifi_rssi:
                updates.append(f"wifi_rssi: {self.wifi_rssi} -> {wifi_rssi} dBm")
            self.wifi_rssi = wifi_rssi
        if thread_rssi is not None:
            if thread_rssi != self.thread_rssi:
                updates.append(f"thread_rssi: {self.thread_rssi} -> {thread_rssi} dBm")
            self.thread_rssi = thread_rssi
        if thread_lqi is not None:
            if thread_lqi != self.thread_lqi:
                updates.append(f"thread_lqi: {self.thread_lqi} -> {thread_lqi}")
            self.thread_lqi = thread_lqi
        if thread_device_type is not None:
            if thread_device_type != self.thread_device_type:
                updates.append(f"thread_device_type: {self.thread_device_type} -> {thread_device_type}")
            self.thread_device_type = thread_device_type
        
        if updates:
            logger.debug("Node %d connectivity updated: %s", self.node_id, ", ".join(updates))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for easy serialization.

        Returns:
            Dictionary representation of the node info
        """
        result = {
            "node_id": self.node_id,
            "unique_id": self.unique_id,
            "available": self.available,
            "date_commissioned": self.date_commissioned,
            "last_interview": self.last_interview,
            "last_seen": self.last_seen.isoformat(),
        }
        # Add connectivity info if available
        if self.device_type is not None:
            result["device_type"] = self.device_type
        if self.wifi_rssi is not None:
            result["wifi_rssi"] = self.wifi_rssi
        if self.thread_rssi is not None:
            result["thread_rssi"] = self.thread_rssi
        if self.thread_lqi is not None:
            result["thread_lqi"] = self.thread_lqi
        if self.thread_device_type is not None:
            result["thread_device_type"] = self.thread_device_type
        return result

    def __repr__(self) -> str:
        return (
            f"NodeInfo(node_id={self.node_id}, unique_id={self.unique_id}, "
            f"available={self.available}, last_seen={self.last_seen})"
        )


class NodeTracker:
    """Tracks the state and availability of Matter nodes."""

    def __init__(self):
        """Initialize the node tracker."""
        self._nodes: dict[int, NodeInfo] = {}
        self._lock = Lock()

    def update_from_nodes_list(self, nodes_data: list[dict[str, Any]]) -> None:
        """Update node information from a nodes list response.

        Args:
            nodes_data: List of node data from get_nodes response
        """
        with self._lock:
            for node in nodes_data:
                if not isinstance(node, dict):
                    continue

                node_id = node.get("node_id")
                if node_id is None:
                    continue

                node_id = int(node_id)

                # Extract unique ID from attributes if available
                attributes = node.get("attributes", {})

                # Look for the identifier attribute at 0/40/18
                unique_id = attributes.get("0/40/18")
                # If we received something and this something is only alphanumeric, use it
                if unique_id is not None and bool(match("^[A-Za-z0-9]*$", str(unique_id))):
                    unique_id = str(unique_id).strip()
                    unique_id = "0x" + unique_id.lower()
                else:
                    unique_id = None

                # Get availability and other info
                available = node.get("available", False)
                date_commissioned = node.get("date_commissioned")
                last_interview = node.get("last_interview")

                # Extract device type from 0/51/0["7"] (WiFi=1, Thread=4)
                device_type = None
                device_type_data = attributes.get("0/51/0")
                logger.debug("Node %d: raw device type data from 0/51/0 = %s", node_id, device_type_data)
                if isinstance(device_type_data, list) and isinstance(device_type_data[0], dict):
                    try:
                        device_type_data = device_type_data[0]  # Consider onldy primary network
                        if "7" in device_type_data and device_type_data["7"] is not None:
                            device_type_val = device_type_data["7"]
                            if device_type_val == "1" or device_type_val == 1:
                                device_type = "wifi"
                            elif device_type_val == "4" or device_type_val == 4:
                                device_type = "thread"
                            logger.debug("Node %d: device type extracted = %s (raw: %s)", node_id, device_type, device_type_val)
                    except (ValueError, TypeError, KeyError) as e:
                        logger.debug("Node %d: failed to extract device type from 0/51/0: %s", node_id, e)

                # Extract WiFi RSSI (0/54/4)
                wifi_rssi = None
                wifi_rssi_val = attributes.get("0/54/4")
                logger.debug("Node %d: raw WiFi RSSI from 0/54/4 = %s", node_id, wifi_rssi_val)
                if wifi_rssi_val is not None:
                    try:
                        wifi_rssi = int(wifi_rssi_val)
                        logger.debug("Node %d: WiFi RSSI extracted = %d dBm", node_id, wifi_rssi)
                    except (ValueError, TypeError) as e:
                        logger.debug("Node %d: failed to extract WiFi RSSI from 0/54/4: %s", node_id, e)

                # Extract Thread LQI and RSSI from 0/53/7 (LQI at ["5"], RSSI at ["6"])
                thread_lqi = None
                thread_rssi = None
                thread_data = attributes.get("0/53/7")
                logger.debug("Node %d: raw Thread metrics from 0/53/7 = %s", node_id, thread_data)
                if isinstance(thread_data, list) and isinstance(thread_data[0], dict):
                    thread_data = thread_data[0]  # Consider only primary network
                    try:
                        if "5" in thread_data and thread_data["5"] is not None:
                            thread_lqi = int(thread_data["5"])
                            logger.debug("Node %d: Thread LQI extracted = %d", node_id, thread_lqi)
                        if "6" in thread_data and thread_data["6"] is not None:
                            thread_rssi = int(thread_data["6"])
                            logger.debug("Node %d: Thread RSSI extracted = %d dBm", node_id, thread_rssi)
                    except (ValueError, TypeError, KeyError) as e:
                        logger.debug("Node %d: failed to extract Thread metrics from 0/53/7: %s", node_id, e)

                # Extract Thread device type (0/53/1)
                thread_device_type = None
                thread_type_val = attributes.get("0/53/1")
                logger.debug("Node %d: raw Thread device type value = %s", node_id, thread_type_val)
                if thread_type_val is not None:
                    try:
                        thread_type_int = int(thread_type_val)
                        thread_type_map = {
                            0: "unspecified",
                            1: "unassigned",
                            2: "sleepy_end_device",
                            3: "end_device",
                            4: "reed",
                            5: "router",
                            6: "leader",
                        }
                        thread_device_type = thread_type_map.get(thread_type_int)
                        logger.debug("Node %d: Thread device type extracted = %s (raw: %d)", node_id, thread_device_type, thread_type_int)
                    except (ValueError, TypeError) as e:
                        logger.debug("Node %d: failed to extract Thread device type from 0/53/1: %s", node_id, e)

                # If node is not available, clear all signal strength indicators
                if not available:
                    wifi_rssi = 0
                    thread_rssi = 0
                    thread_lqi = 0
                    logger.debug("Node %d: unavailable, RSSI/LQI set to 0", node_id)

                # Update or create node info
                if node_id in self._nodes:
                    node_info = self._nodes[node_id]
                    old_available = node_info.available
                    # Update availability and last_seen
                    node_info.update_availability(available)
                    if available != old_available:
                        logger.info("Node %d availability changed: %s -> %s, last_seen updated to %s",
                                   node_id, old_available, available, node_info.last_seen.isoformat())
                    else:
                        logger.debug("Node %d still available, last_seen updated to %s",
                                    node_id, node_info.last_seen.isoformat())
                    # Update other fields if provided
                    if unique_id is not None:
                        node_info.unique_id = unique_id
                    else:
                        node_info.unique_id = node_id
                    if date_commissioned is not None:
                        node_info.date_commissioned = date_commissioned
                    if last_interview is not None:
                        node_info.last_interview = last_interview
                    # Update connectivity info
                    node_info.update_connectivity_info(
                        device_type=device_type,
                        wifi_rssi=wifi_rssi,
                        thread_rssi=thread_rssi,
                        thread_lqi=thread_lqi,
                        thread_device_type=thread_device_type,
                    )
                    logger.debug(
                        "Updated node %d: available=%s, unique_id=%s",
                        node_id,
                        available,
                        unique_id,
                    )
                else:
                    if unique_id is None:
                        unique_id = node_id

                    # Create new node info
                    node_info = NodeInfo(
                        node_id=node_id,
                        unique_id=unique_id,
                        available=available,
                        date_commissioned=date_commissioned,
                        last_interview=last_interview,
                    )
                    # Set connectivity info
                    node_info.update_connectivity_info(
                        device_type=device_type,
                        wifi_rssi=wifi_rssi,
                        thread_rssi=thread_rssi,
                        thread_lqi=thread_lqi,
                        thread_device_type=thread_device_type,
                    )
                    self._nodes[node_id] = node_info
                    logger.info(
                        "Discovered new node %d: unique_id=%s, available=%s",
                        node_id,
                        unique_id,
                        available,
                    )

    def mark_node_attribute_update(self, node_id: int) -> bool:
        """Mark that a node sent an attribute update (update last_seen and availability).

        Args:
            node_id: The node ID that sent the update

        Returns:
            True if the node's availability changed from offline to online, False otherwise
        """
        with self._lock:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                was_offline = not node.available
                
                # If node was offline, mark it as available now
                if was_offline:
                    node.update_availability(True)
                    logger.info("Node %d: came online (was offline, received attribute update)", node_id)
                    return True
                else:
                    # Node was already online, just update last_seen
                    node.update_last_seen()
                    logger.debug("Node %d: last_seen updated to %s (from attribute update)", 
                                node_id, node.last_seen.isoformat())
                    return False
            else:
                logger.debug(
                    "Received attribute update from unknown node %d, creating entry",
                    node_id,
                )
                # Create a new entry for this node if we haven't seen it before
                node_info = NodeInfo(node_id=node_id, available=True)
                self._nodes[node_id] = node_info
                logger.info("Node %d: created from attribute update, last_seen = %s", 
                           node_id, node_info.last_seen.isoformat())
                return False

    def update_node_attribute(self, node_id: int, cluster_id: str, attribute_id: str, value: Any) -> None:
        """Update a specific node attribute value (for signal metrics like RSSI/LQI).

        This method is called when individual attribute updates arrive and extracts signal
        metrics (WiFi RSSI, Thread RSSI, Thread LQI) to keep them current between polling cycles.

        Args:
            node_id: The node ID
            cluster_id: The cluster ID (e.g., "0x0054", "53" or "0x0053")
            attribute_id: The attribute ID (e.g., "0x0004", "4" or "0x0537")
            value: The attribute value
        """
        with self._lock:
            if node_id not in self._nodes:
                logger.debug("Node %d not found for attribute update (cluster %s, attr %s)", 
                           node_id, cluster_id, attribute_id)
                return
            
            node = self._nodes[node_id]
            
            # Normalize cluster and attribute IDs to decimal strings
            cluster_dec = self._normalize_id(cluster_id)
            attr_dec = self._normalize_id(attribute_id)
            
            # WiFi RSSI: cluster 0x0054 (84 dec), attribute 0x0004 (4 dec)
            if cluster_dec == "84" and attr_dec == "4":
                try:
                    rssi_val = int(value)
                    if rssi_val != node.wifi_rssi:
                        logger.info("Node %d: WiFi RSSI updated from %s to %d dBm (from attribute update)", 
                                   node_id, node.wifi_rssi, rssi_val)
                        node.wifi_rssi = rssi_val
                    else:
                        logger.debug("Node %d: WiFi RSSI refreshed = %d dBm", node_id, rssi_val)
                except (ValueError, TypeError) as e:
                    logger.debug("Node %d: failed to parse WiFi RSSI value %s: %s", node_id, value, e)
            
            # Thread device type: cluster 0x0053 (83 dec), attribute 0x0001 (1 dec)
            elif cluster_dec == "83" and attr_dec == "1":
                try:
                    thread_type_int = int(value)
                    thread_type_map = {
                        0: "unspecified",
                        1: "unassigned",
                        2: "sleepy_end_device",
                        3: "end_device",
                        4: "reed",
                        5: "router",
                        6: "leader",
                    }
                    thread_device_type = thread_type_map.get(thread_type_int)
                    if thread_device_type != node.thread_device_type:
                        logger.info("Node %d: Thread device type updated from %s to %s (from attribute update)", 
                                   node_id, node.thread_device_type, thread_device_type)
                        node.thread_device_type = thread_device_type
                    else:
                        logger.debug("Node %d: Thread device type refreshed = %s", node_id, thread_device_type)
                except (ValueError, TypeError) as e:
                    logger.debug("Node %d: failed to parse Thread device type value %s: %s", node_id, value, e)
            
            # Thread metrics are typically structs, handle them at the structure level
            # Note: Individual Thread metric fields (LQI, RSSI) come as nested struct updates
            # which may not be easily parseable from a single attribute update

    @staticmethod
    def _normalize_id(id_value: str) -> str:
        """Convert cluster/attribute ID to decimal string format.

        Args:
            id_value: ID as string, could be "0x0054", "84", "0x54", etc.

        Returns:
            Decimal string representation (e.g., "84")
        """
        if isinstance(id_value, str):
            # Remove leading 0x if present
            if id_value.startswith("0x") or id_value.startswith("0X"):
                try:
                    return str(int(id_value, 16))
                except ValueError:
                    return id_value
            # Try to parse as decimal
            try:
                return str(int(id_value))
            except ValueError:
                return id_value
        else:
            return str(id_value)

    def get_node(self, node_id: int) -> Optional[NodeInfo]:
        """Get information about a specific node.

        Args:
            node_id: The node ID to retrieve

        Returns:
            NodeInfo if found, None otherwise
        """
        with self._lock:
            return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[NodeInfo]:
        """Get information about all known nodes.

        Returns:
            List of NodeInfo objects
        """
        with self._lock:
            return list(self._nodes.values())

    def get_available_nodes(self) -> list[NodeInfo]:
        """Get information about all available nodes.

        Returns:
            List of available NodeInfo objects
        """
        with self._lock:
            return [node for node in self._nodes.values() if node.available]

    def get_unavailable_nodes(self) -> list[NodeInfo]:
        """Get information about all unavailable nodes.

        Returns:
            List of unavailable NodeInfo objects
        """
        with self._lock:
            return [node for node in self._nodes.values() if not node.available]

    def get_nodes_as_dicts(self) -> list[dict[str, Any]]:
        """Get all nodes as list of dictionaries.

        Returns:
            List of node dictionaries
        """
        with self._lock:
            return [node.to_dict() for node in self._nodes.values()]

    def clear(self) -> None:
        """Clear all tracked nodes."""
        with self._lock:
            self._nodes.clear()

    def __len__(self) -> int:
        """Get the number of tracked nodes."""
        with self._lock:
            return len(self._nodes)

    def __repr__(self) -> str:
        with self._lock:
            total = len(self._nodes)
            available = sum(1 for n in self._nodes.values() if n.available)
        return f"NodeTracker(total={total}, available={available})"
