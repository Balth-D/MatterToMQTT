"""Matter WebSocket to MQTT Bridge.

This package bridges Matter device attributes to MQTT topics in both directions:
- Attributes to MQTT: Device updates published as MQTT messages
- MQTT to Attributes: Commands from MQTT can be sent to devices
"""

__version__ = "2.1.0"
__author__ = "Matter to MQTT Bridge Contributors"

from .config import Config
from .attribute_filter import AttributeFilter
from .device_manager import DeviceManager
from .mqtt_bridge import MQTTBridge
from .matter_client import MatterClient, AttributeUpdate
from .command_handler import CommandRouter, MQTTCommand

__all__ = [
    "Config",
    "AttributeFilter",
    "DeviceManager",
    "MQTTBridge",
    "MatterClient",
    "AttributeUpdate",
    "CommandRouter",
    "MQTTCommand",
]
