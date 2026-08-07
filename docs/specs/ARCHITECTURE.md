# Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Matter WebSocket Server                     │
└────────────────────────┬────────────────────────────────────┘
                         │ (WebSocket)
                         │
┌────────────────────────▼────────────────────────────────────┐
│              MatterClient (matter_client.py)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • consume_messages()                                 │   │
│  │ • parse_attribute_update()                           │   │
│  │ • Yields AttributeUpdate objects                     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│            MatterToMQTTApp (main.py)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • run() - main event loop                            │  │
│  │ • _on_nodes_list() - initial nodes processing       │  │
│  │ • _on_attribute_update() - attribute processing     │  │
│  └──────────────────────────────────────────────────────┘  │
│                       ▲ ▲ ▲                                │
│         ┌─────────────┘ │ └──────────────┐                │
│         │               │                 │                │
│         ▼               ▼                 ▼                │
│   ┌─────────────┐ ┌──────────────┐ ┌───────────┐        │
│   │DeviceManager│ │AttributeFilter│ │MQTTBridge │        │
│   │             │ │               │ │           │        │
│   │Uses:Config  │ │Uses:Config    │ │Uses:Config│        │
│   └─────────────┘ └──────────────┘ └───────────┘        │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                    MQTT Broker                              │
└────────────────────────────────────────────────────────────┘
```

## Component Interactions

### 1. Initialization Flow

```
main()
  │
  ├─► build_parser()
  │     └─► Parse CLI arguments
  │
  ├─► LoggerConfig.setup()
  │     └─► Initialize logging
  │
  ├─► Config.from_args()
  │     └─► Create Config object
  │
  └─► MatterToMQTTApp(config)
        ├─► Create DeviceManager
        ├─► Create AttributeFilter (from file)
        ├─► Create MatterClient
        └─► Setup MQTTBridge (if not dry-run)
```

### 2. Runtime Flow

```
app.run()
  │
  ├─► Setup signal handlers
  │     └─► SIGINT, SIGTERM → stop_event.set()
  │
  ├─► MQTT connection (if not dry-run)
  │     └─► MQTTBridge.connect()
  │
  └─► matter_client.consume_messages()
        │
        ├─► Connect to WebSocket
        │     └─► app._on_nodes_list(nodes)
        │           └─► DeviceManager.cache_node_identifiers()
        │
        └─► Event loop (until stop_event)
              │
              ├─► Receive WebSocket message
              │     │
              │     └─► MatterClient.parse_attribute_update()
              │           │
              │           └─► app._on_attribute_update(update)
              │                 │
              │                 ├─► Skip cluster 0
              │                 │
              │                 ├─► AttributeFilter.is_allowed()
              │                 │
              │                 ├─► DeviceManager.get_device_identifier()
              │                 │
              │                 ├─► Build MQTT topic
              │                 │
              │                 └─► MQTTBridge.publish()
              │
              └─► (repeat until stop_event or connection lost)
```

### 3. Attribute Update Processing

```
AttributeUpdate from Matter Server
  │
  ├─► Check: cluster_id == "0"?
  │     └─► If yes, skip
  │
  ├─► Check: is_allowed(cluster_id, attribute_id)?
  │     └─► If no, skip
  │
  ├─► Get device identifier
  │     └─► DeviceManager.get_device_identifier(node_id)
  │           └─► Returns cached identifier or node_id
  │
  ├─► Get cluster/attribute names
  │     ├─► AttributeFilter.get_cluster_name()
  │     └─► AttributeFilter.get_attribute_name()
  │
  ├─► Build topic
  │     ├─► Check: simple_endpoints?
  │     │     ├─► If yes: prefix/device/cluster/attribute
  │     │     └─► If no: prefix/device/endpoint/cluster/attribute
  │
  └─► Publish to MQTT
        └─► MQTTBridge.publish(topic, payload)
```

## Class Responsibilities

### Config (config.py)
**Responsibility**: Store and provide access to configuration

**Attributes**:
- `url_ws`: Matter WebSocket URL
- `url_mqtt`: MQTT broker URL
- `mqtt_topic_prefix`: Prefix for MQTT topics
- `mqtt_user`, `mqtt_password`: MQTT credentials
- `filter_file`: Path to attribute filter JSON
- `debug_level`: Logging level
- `dry_run`: Test mode without MQTT
- `reconnect_delay`: Seconds between reconnects

**Public Methods**:
- `from_args(args)`: Create from argparse Namespace

### AttributeFilter (attribute_filter.py)
**Responsibility**: Manage attribute filtering and naming

**State**:
- `filter_data`: Loaded filter dictionary

**Public Methods**:
- `from_file(filter_file)`: Load filter from JSON
- `is_allowed(cluster_id, attribute_id)`: Check if attribute should be published
- `get_cluster_name(cluster_id)`: Get human-readable cluster name
- `get_attribute_name(cluster_id, attribute_id)`: Get human-readable attribute name

### DeviceManager (device_manager.py)
**Responsibility**: Track devices and their properties

**State**:
- `_node_identifier_cache`: Mapping of node_id → device_identifier
- `_devices_simple_endpoints`: Mapping of node_id → has_only_endpoints_0_and_1

**Public Methods**:
- `cache_node_identifiers(nodes_data)`: Load initial node data
- `get_device_identifier(node_id)`: Get identifier or node_id as fallback
- `has_simple_endpoints(node_id)`: Check if device is "simple"
- `clear_cache()`: Reset all cached data

### MQTTBridge (mqtt_bridge.py)
**Responsibility**: Handle MQTT connection and publishing

**State**:
- `host`, `port`: MQTT broker address
- `username`, `password`: MQTT credentials
- `client`: paho.mqtt.Client instance
- `_is_connected`: Connection status

**Public Methods**:
- `connect()`: Connect to MQTT broker
- `disconnect()`: Close MQTT connection
- `publish(topic, payload, qos, retain)`: Publish message
- `is_connected()`: Check connection status

### MatterClient (matter_client.py)
**Responsibility**: WebSocket communication with Matter server

**Classes**:
- `AttributeUpdate`: Data class with update information
  - Fields: `node_id`, `endpoint_id`, `cluster_id`, `attribute_id`, `value`

**Public Methods**:
- `consume_messages(on_nodes_list, on_attribute_update, stop_event)`: Main event loop
- `parse_attribute_update(message)`: Parse single update
- `iter_attribute_updates(message)`: Yield updates from message

### MatterToMQTTApp (main.py)
**Responsibility**: Orchestrate all components and implement business logic

**Attributes**:
- `config`: Configuration object
- `device_manager`: Device manager instance
- `attribute_filter`: Attribute filter instance
- `matter_client`: Matter WebSocket client
- `mqtt_bridge`: MQTT bridge instance
- `stop_event`: Asyncio event for shutdown

**Public Methods**:
- `run()`: Main application loop

**Private Methods**:
- `_on_nodes_list(nodes)`: Handle initial nodes
- `_on_attribute_update(update)`: Handle attribute update

## Data Flow Examples

### Example 1: Simple Device Update

```
Matter Server sends:
  {
    "event": "attribute_updated",
    "data": [1, "1/0x000F/0x0055", true]
  }

↓ MatterClient.parse_attribute_update()

AttributeUpdate:
  node_id: "1"
  endpoint_id: "1"
  cluster_id: "15" (normalized from 0x000F)
  attribute_id: "85" (normalized from 0x0055)
  value: true

↓ app._on_attribute_update()

Check filters:
  - Not cluster 0 ✓
  - Is allowed ✓
  - Get device ID: "ABC123"
  - Get names: "level", "current_level"

MQTT topic:
  "matter/ABC123/1/level/current_level"

MQTT payload:
  true
```

### Example 2: Temperature Sensor

```
Filter config:
  "0x0402": {
    "name": "temperature",
    "attributes": {
      "0x0000": "measured_value"
    }
  }

Matter update arrives:
  cluster_id: "1026" (0x0402)
  attribute_id: "0" (0x0000)
  value: 2150

Processing:
  - Device ID: "LivingRoom_Temp"
  - Cluster name: "temperature"
  - Attribute name: "measured_value"
  - Is simple device: true (no endpoint in topic)

MQTT publication:
  Topic: "matter/LivingRoom_Temp/temperature/measured_value"
  Payload: 2150
```

## Error Handling Strategy

### WebSocket Errors
- Connection lost → Reconnect after delay
- JSON parse error → Log and continue
- Timeout on initial nodes → Retry up to 10 times

### MQTT Errors
- Connection failed → Application exits with error
- Publish failed → Logged, but doesn't stop processing

### Configuration Errors
- Filter file not found → Continue with no filter
- Invalid JSON → Continue with no filter
- Invalid arguments → Application exits

## Extension Points

### Adding a New Data Source
1. Create new client class similar to `MatterClient`
2. Emit `AttributeUpdate` objects
3. Subscribe in `MatterToMQTTApp._on_attribute_update()`

### Adding New MQTT Logic
1. Extend `MQTTBridge` with new publish methods
2. Or create wrapper class in `main.py`

### Adding New Filtering Criteria
1. Extend `AttributeFilter` with new methods
2. Call from `_on_attribute_update()`

### Adding Device Management
1. Extend `DeviceManager` class
2. Call from initialization or update methods
