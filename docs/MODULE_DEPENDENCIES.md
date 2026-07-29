# Module Dependency Graph

## Import Structure (No Circular Dependencies)

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (Entry Point)                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Imports: config, logger_config, attribute_filter,  │ │
│  │    device_manager, mqtt_bridge, matter_client,     │ │
│  │    command_handler (NEW v2.1), utils               │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

**Note:** The diagram above shows the 6 core modules. Additionally:
- **command_handler.py** (NEW in v2.1) is imported by main.py for bidirectional command support
- See "[Class Hierarchy](#class-hierarchy)" section below for command_handler module details
  │ │ │ │ │ └─────────────────────────────────────┐
  │ │ │ │ │                                       │
  │ │ │ │ └──────────────────────────────┐        │
  │ │ │ │                                │        │
  │ │ │ └────────────────────────┐       │        │
  │ │ │                          │       │        │
  │ │ └──────────────┐           │       │        │
  │ │               │           │       │        │
  │ │               ▼           │       │        │
  │ │           ┌─────────────────────────────────┐
  │ │           │ config.py                       │
  │ │           │ Imports: argparse               │
  │ │           └─────────────────────────────────┘
  │ │
  │ │               ┌─────────────────────────────────┐
  │ └──────────────►│ logger_config.py                │
  │                │ Imports: logging                │
  │                └─────────────────────────────────┘
  │
  │               ┌─────────────────────────────────┐
  ├──────────────►│ attribute_filter.py              │
  │               │ Imports: json, logging, utils    │
  │               └─────────────────────────────────┘
  │
  │               ┌─────────────────────────────────┐
  ├──────────────►│ device_manager.py                │
  │               │ Imports: logging                │
  │               └─────────────────────────────────┘
  │
  │               ┌─────────────────────────────────┐
  ├──────────────►│ mqtt_bridge.py                   │
  │               │ Imports: logging, urlparse,      │
  │               │         paho.mqtt.client        │
  │               └─────────────────────────────────┘
  │
  │               ┌─────────────────────────────────┐
  └──────────────►│ matter_client.py                 │
                  │ Imports: asyncio, json,         │
                  │         logging, websockets,    │
                  │         utils                   │
                  └─────────────────────────────────┘
                    ▲
                    │
                    └─────────────────────────────────┐
                                                      │
                       ┌──────────────────────────────┴────────────────┐
                       │                                               │
                  ┌────────────────────┐                   ┌───────────────────┐
                  │ utils.py           │                   │ __init__.py        │
                  │ Imports: json      │                   │ Re-exports classes │
                  └────────────────────┘                   └───────────────────┘
```

## Dependency Level Summary

**Level 0 (No dependencies except stdlib):**
- `logger_config.py` (logging)
- `device_manager.py` (logging)
- `config.py` (argparse)
- `utils.py` (json)

**Level 1 (Depends on Level 0):**
- `attribute_filter.py` (uses utils)
- `mqtt_bridge.py` (logging, urlparse, paho)
- `matter_client.py` (uses utils)
- `command_handler.py` (uses utils, typing)

**Level 2 (Depends on Level 0-1):**
- `main.py` (uses all modules including command_handler)

**Entry Point:**
- `__init__.py` (re-exports Level 1-2 classes)

## Class Hierarchy

```
No inheritance hierarchy (composition-based design):

main.py
├── MatterToMQTTApp
│   ├── has Config
│   ├── has DeviceManager
│   ├── has AttributeFilter
│   ├── has MatterClient
│   ├── has MQTTBridge
│   └── has CommandRouter

config.py
├── Config (dataclass)
└── build_parser()

logger_config.py
└── LoggerConfig (utility class with static methods)

attribute_filter.py
└── AttributeFilter

device_manager.py
└── DeviceManager

mqtt_bridge.py
└── MQTTBridge

matter_client.py
├── AttributeUpdate (dataclass)
└── MatterClient
  - send_device_command() - NEW in v2.1

command_handler.py - NEW in v2.1 (Bidirectional Support)
├── CommandRouter
│   └── parse_mqtt_command(topic, payload, node_id_lookup)
├── CommandTopicParser
│   ├── parse_command_topic(topic, prefix)
│   │   - Supports full format: prefix/device/endpoint/cluster/command
│   │   - Supports simple format: prefix/device/cluster/command (defaults to endpoint 1)
│   └── parse_command_payload(payload)
└── MQTTCommand (dataclass)
    ├── node_id
    ├── endpoint_id
    ├── cluster_id
    ├── command_name
    └── payload

command_handler.py
├── CommandRouter
├── CommandTopicParser
└── MQTTCommand (dataclass)

utils.py
└── Helper functions

__init__.py
└── Package exports
```

## Message Flow Diagram

### Download (Matter → MQTT)
```
Matter Server
     │
     │ WebSocket
     ▼
┌─────────────────┐
│ MatterClient    │
│ • consume_msgs()│
└─────┬───────────┘
      │ parse_attribute_update()
      │ AttributeUpdate object
      ▼
┌──────────────────────────────────┐
│ MatterToMQTTApp                  │
│ • _on_attribute_update()         │
│                                  │
│ 1. Check cluster!=0    ✓         │
│ 2. is_allowed() ──────────────── ├──► AttributeFilter
│                        ✓         │
│ 3. get_device_identifier() ──── ├──► DeviceManager
│                        ✓         │
│ 4. get_cluster_name() ────────── ├──► AttributeFilter
│ 5. get_attribute_name() ──────── ┤
│                        ✓         │
│ 6. has_simple_endpoints() ────── ├──► DeviceManager
│                        ✓         │
│ 7. build_topic()        ✓        │
│ 8. publish() ──────────────────┐ │
└──────────────────────────────┬──┘
                               │
                    ┌──────────▼─────────┐
                    │ MQTTBridge         │
                    │ • publish(topic)   │
                    └────────────────────┘
                             │
                             ▼
                        MQTT Broker
```

### Upload (MQTT → Matter)
```
MQTT Broker
     │
     ├─ Subscribe: matter/+/+/+/command (and matter/+/+/command for simple devices)
     │
     ▼
┌────────────────────┐
│ MQTTBridge         │
│ • on_message()     │
└─────┬──────────────┘
      │ topic, payload
      ▼
┌─────────────────────────────────────────┐
│ MatterToMQTTApp._on_mqtt_message()      │
│                                         │
│ • CommandRouter.parse_mqtt_command()    │
│   ├── Parse topic ────────────────────┐ │
│   │   (CommandTopicParser)            │ │
│   │                                   │ │
│   ├── Parse payload ──────────────────┤─├──► CommandTopicParser
│   │   (JSON)                         │ │
│   │                                   │ │
│   ├── Lookup node_id ────────────────┐ │
│   │   from device_id                 │ │
│   │   (DeviceManager)                │ │
│   │                                   │ │
│   └── Create MQTTCommand ────────────┘ │
│       (device_id → node_id mapping)    │
│                                         │
│ • send_command_to_device()              │
│   ├── Check dry-run                    │
│   └── Call MatterClient.send_device_
│       command()                        │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────▼──────────┐
        │ MatterClient        │
        │ • send_device_cmd() │
        │                     │
        │ Create WebSocket    │
        │ message with:       │
        │ - node_id           │
        │ - endpoint_id       │
        │ - cluster_id        │
        │ - command_name      │
        │ - payload           │
        └────────────┬────────┘
                     │
                     ▼
              Matter Server
                     │
                     ▼
              Matter Device
```

## Configuration Flow

```
CLI Arguments (argparse)
        │
        ▼
build_parser()
        │
        ▼
  argparse.Namespace
        │
        ▼
Config.from_args()
        │
        ▼
    Config object
        │
        ├──► MatterToMQTTApp.__init__()
        ├──► AttributeFilter.from_file(config.filter_file)
        ├──► LoggerConfig.setup(config.debug_level)
        ├──► MatterClient(config.url_ws, config.reconnect_delay)
        ├──► MQTTBridge(config.url_mqtt, config.mqtt_user, config.mqtt_password)
        └──► App ready to run
```

## Async Flow

```
asyncio.run(main_async(args))
        │
        ▼
MatterToMQTTApp.run()
        │
        ├─► Setup signal handlers
        │
        ├─► MQTTBridge.connect() (if not dry-run)
        │
        └─► matter_client.consume_messages()
                │
                ├─► Connect to WebSocket
                │
                ├─► Send start_listening command
                │
                ├─► Wait for initial message_id=3
                │       │
                │       └─► on_nodes_list() callback
                │           DeviceManager.cache_node_identifiers()
                │
                └─► Main async loop (until stop_event)
                        │
                        ├─► websocket.recv() (awaiting)
                        │
                        ├─► Parse message
                        │
                        ├─► on_attribute_update() callback
                        │       │
                        │       └─► MQTTBridge.publish()
                        │
                        └─► (repeat until stop_event or connection lost)
```

## State Management

```
Global State (per instance, no globals!)
├── DeviceManager
│   ├── _node_identifier_cache: dict[node_id → device_id]
│   └── _devices_simple_endpoints: dict[node_id → bool]
│
├── AttributeFilter
│   └── filter_data: dict[cluster_id → {name, attributes}]
│
└── Config (immutable dataclass)
    ├── url_ws, url_mqtt, mqtt_topic_prefix
    ├── mqtt_user, mqtt_password, filter_file
    ├── debug_level, dry_run, reconnect_delay
    └── ...
```

## Error Handling Paths

```
WebSocket Error
    │
    ├─► ConnectionClosed
    │   └─► Log warning
    │   └─► Reconnect after delay
    │
    ├─► JSON Decode Error
    │   └─► Log warning, skip message
    │
    ├─► Timeout on initial nodes
    │   └─► Retry up to 10 times
    │
    └─► Network Error (OSError)
        └─► Reconnect after delay

MQTT Error
    │
    ├─► Connection Failed
    │   └─► Return error code 1
    │
    ├─► Publish Failed
    │   └─► Log error, continue
    │
    └─► Auth Failed
        └─► Log and exit

Configuration Error
    │
    ├─► Filter file not found
    │   └─► Continue with no filter
    │
    ├─► Invalid JSON
    │   └─► Continue with no filter
    │
    └─► Invalid arguments
        └─► Print help and exit
```

## Testing Coverage Map

```
Core Logic:
├── config.py
│   └── Config.from_args() ─► Unit test
│   └── build_parser() ─► CLI test
│
├── utils.py
│   ├── normalize_id() ─► Unit test
│   ├── safe_json() ─► Unit test
│   └── parse_path_fields() ─► Unit test
│
├── attribute_filter.py
│   ├── AttributeFilter.from_file() ─► Unit test
│   ├── is_allowed() ─► Unit test
│   └── get_*_name() ─► Unit test
│
├── device_manager.py
│   ├── cache_node_identifiers() ─► Unit test
│   ├── get_device_identifier() ─► Unit test
│   ├── has_simple_endpoints() ─► Unit test
│   └── get_node_id_by_device_identifier() ─► Unit test (NEW v2.1)
│
├── mqtt_bridge.py
│   ├── Connection handling ─► Integration test
│   └── publish() ─► Integration test (mock)
│
├── matter_client.py
│   ├── parse_attribute_update() ─► Unit test
│   ├── send_device_command() ─► Unit test (NEW v2.1)
│   ├── WebSocket handling ─► Integration test (mock)
│   └── Message processing ─► Unit test
│
└── command_handler.py (NEW v2.1)
    ├── CommandTopicParser.parse_command_topic() ─► Unit test (9 tests)
    ├── CommandTopicParser.parse_command_payload() ─► Unit test
    ├── CommandRouter.parse_mqtt_command() ─► Unit test
    ├── Dual-format support ─► Unit tests (simple + full)
    └── End-to-end command routing ─► Integration test

Integration:
└── main.py
    ├── MatterToMQTTApp.run() ─► Integration test
    ├── _on_nodes_list() ─► Integration test
    └── _on_attribute_update() ─► Integration test
```
