# Matter WebSocket to MQTT Bridge

A Python application that bridges Matter devices with MQTT, enabling full-duplex bidirectional communication:
- **Download (Matter → MQTT):** Device attribute updates are published to MQTT
- **Upload (MQTT → Matter):** Commands published to MQTT are sent to Matter devices

Automatically detects device identifiers and handles both simple single-endpoint and complex multi-endpoint devices with intelligent topic structure.

## Disclainer

This project was made mainly by Copilot. Use it at your own risk!

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd MatterToMQTT

# Create and activate a Python environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Quick Usage

```bash
# Using default config (config.yaml)
python3 main.py

# Using custom config file
python3 main.py /path/to/config.yaml

# Dry run mode - test without sending to MQTT
# (set dry_run: true in config.yaml)
python3 main.py config.yaml --help  # shows help with new config system
```

## Configuration

Configuration is managed via a YAML file (see [config.yaml](config.yaml) for defaults).

### Example Configuration

```yaml
# Matter server
matter:
  url: ws://192.168.1.50:5580/ws
  reconnect_delay: 5.0

# MQTT broker
mqtt:
  url: mqtt://192.168.1.100:1883
  topic_prefix: matter
  username: homeassistant
  password: secure_password

# Attribute filtering
attributes:
  filter: examples/attributes_filter_example.json

# Logging
logging:
  level: info  # debug, info, warning, error

# Advanced settings
advanced:
  dry_run: false  # Test mode
```

### Running with Custom Config

```bash
# Create custom configuration
cp config.yaml my_config.yaml
nano my_config.yaml

# Run with custom config
python3 main.py my_config.yaml
```

### Configuration File Locations

The application looks for `config.yaml` in the working directory by default:

```bash
# Recommended structure for production
/opt/MatterToMQTT/
├── config.yaml           # Main configuration
├── config.production.yaml # Production override
├── main.py
├── src/
└── venv/
```

## Features

✓ **Bidirectional Communication**
- Publish Matter device attributes to MQTT
- Send MQTT commands to Matter devices

✓ **Automatic Device Detection**
- Caches device identifiers (0/40/18 attribute)
- Detects single vs multi-endpoint devices
- Handles endpoint mapping intelligently

✓ **Flexible Topic Structure**
- Simple format for single-endpoint devices: `matter/device/cluster/command`
- Full format for multi-endpoint: `matter/device/endpoint/cluster/command`
- Human-readable cluster/attribute names

✓ **Attribute Filtering**
- Optional JSON filter for selective publishing
- Supports cluster and attribute whitelisting

✓ **Robust Connection Handling**
- Automatic reconnection on failures
- Graceful shutdown with signal handling
- Configurable reconnect delays

## Command Line

```bash
# Show help
python3 main.py --help

# Run with default config.yaml
python3 main.py

# Run with custom config file
python3 main.py /path/to/custom/config.yaml
```

## Documentation

- **[Installation & Setup](docs/INSTALLATION.md)** - Systemd service, auto-start, production deployment
- **[Architecture](docs/ARCHITECTURE.md)** - System design and component overview
- **[Bidirectional Guide](docs/BIDIRECTIONAL_GUIDE.md)** - Full guide to command sending (download & upload)
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Copy-paste command examples
- **[Module Dependencies](docs/MODULE_DEPENDENCIES.md)** - Dependency graph and data flow
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Contributing and extending the code

## Examples

### Publish Attributes (Matter → MQTT)

Automatically published by the bridge:

```
matter/light_123/on_off/state              → true
matter/light_123/level_control/level       → 200
matter/sensor_456/temperature/measured     → 22.5
```

### Send Commands (MQTT → Matter)

**Simple format** (endpoint defaults to 1):

```bash
mosquitto_pub -t "matter/light_123/6/command" \
  -m '{"command":"On","payload":{}}'

mosquitto_pub -t "matter/light_123/8/command" \
  -m '{"command":"MoveToLevel","payload":{"level":200,"transition_time":0}}'
```

**Full format** (explicit endpoint):

```bash
mosquitto_pub -t "matter/device/1/6/command" \
  -m '{"command":"On","payload":{}}'

mosquitto_pub -t "matter/bridge/2/8/command" \
  -m '{"command":"MoveToLevel","payload":{"level":150,"transition_time":0}}'
```

## Testing

```bash
# Run unit tests
python3 tests/test_commands.py

# Run command examples
python3 examples/example_commands.py <hostname> <port>
```

## MQTT Topic Structure

### Download (Attributes)

**Simple devices** (endpoints 0-1):
```
matter/<device_id>/<cluster>/<attribute>
```

**Multi-endpoint devices**:
```
matter/<device_id>/<endpoint>/<cluster>/<attribute>
```

### Upload (Commands)

**Simple format**:
```
matter/<device_id>/<cluster>/command
```

**Full format**:
```
matter/<device_id>/<endpoint>/<cluster>/command
```

## Project Structure

```
MatterToMQTT/
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
├── README.md               # This file
│
├── src/                    # Python source code
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── logger_config.py    # Logging setup
│   ├── attribute_filter.py # Attribute filtering
│   ├── device_manager.py   # Device tracking
│   ├── mqtt_bridge.py      # MQTT communication
│   ├── matter_client.py    # Matter WebSocket client
│   ├── command_handler.py  # Command parsing & routing
│   └── utils.py            # Utility functions
│
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── BIDIRECTIONAL_GUIDE.md
│   ├── QUICK_REFERENCE.md
│   ├── MODULE_DEPENDENCIES.md
│   └── DEVELOPER_GUIDE.md
│
├── tests/                  # Unit tests
│   └── test_commands.py
│
└── examples/               # Examples
    ├── example_commands.py
    └── attributes_filter_example.json
```

## Requirements

- Python 3.10+
- [paho-mqtt](https://github.com/eclipse/paho.mqtt.python)
- [websockets](https://github.com/python-websockets/websockets)
- [python-matter-server](https://github.com/matter-js/python-matter-server) (running separately)

## Configuration Example

Filter file (`attributes_filter_example.json`):

```json
{
  "0x0006": {
    "name": "on_off",
    "attributes": {
      "0x0000": "state"
    }
  },
  "0x0008": {
    "name": "level_control",
    "attributes": {
      "0x0000": "current_level",
      "0x000F": "options"
    }
  },
  "0x0402": {
    "name": "temperature",
    "attributes": {
      "0x0000": "measured_value"
    }
  }
}
```

## Troubleshooting

### Connection Issues

```bash
# Check Matter server connectivity
python3 main.py --debug debug 2>&1 | grep -i "connected\|error"

# Test MQTT broker
mosquitto_pub -h <broker> -t test -m "hello"
```

### Commands Not Sending

```bash
# Enable debug logging
python3 main.py --debug debug

# Check device ID caching
python3 main.py --debug debug 2>&1 | grep "Cached identifier"

# Dry run to test without MQTT
python3 main.py --dry-run --debug debug
```

## Development

See [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for:
- Contributing guidelines
- Adding new modules
- Extending functionality
- Testing new features

## License

Licensed under GPLv3

## Support

For issues and questions, refer to:
- [BIDIRECTIONAL_GUIDE.md](docs/BIDIRECTIONAL_GUIDE.md) - For command examples
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - For system design details
- [MODULE_DEPENDENCIES.md](docs/MODULE_DEPENDENCIES.md) - For code structure

---

**Version 2.1.1** - Full duplex bidirectional communication with dual-format topic support
