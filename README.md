# Matter WebSocket to MQTT Bridge

A Python application that bridges Matter devices with MQTT, enabling full-duplex bidirectional communication with real-time device monitoring.

## ✨ Key Features

- **🔄 Bidirectional Communication**: Attribute updates flow Matter → MQTT, commands flow MQTT → Matter
- **📊 Node Monitoring**: Automatic discovery and periodic polling of all Matter devices with availability tracking
- **⏱️ Real-time Updates**: Track last-seen timestamps and connectivity status for each device
- **📡 Signal Metrics**: Publish WiFi RSSI, Thread RSSI, and Thread LQI signal quality metrics
- **🎯 Smart Topics**: Automatically detects device identifiers and uses intelligent topic hierarchy
- **🔧 Flexible Filtering**: Configurable attribute filtering for selective attribute publishing
- **🌐 Multi-endpoint Support**: Handles both simple single-endpoint and complex multi-endpoint Matter devices
- **⚙️ Highly Configurable**: YAML-based configuration with sensible defaults

## Disclaimer

This project was made mainly by Copilot. Use it at your own risk!

## 📚 Documentation

### For Users & Developers

Start here to get up and running:

- **[Getting Started](docs/guides/INSTALLATION.md)** - Installation and initial setup
- **[User Guide](docs/guides/QUICK_REFERENCE.md)** - Common tasks and configuration
- **[Matter → MQTT](docs/guides/MATTER_MQTT_README.md)** - Publishing device attributes to MQTT
- **[MQTT → Matter](docs/guides/BIDIRECTIONAL_GUIDE.md)** - Sending commands to devices via MQTT
- **[Node Tracking](docs/guides/NODE_TRACKER_QUICK_REFERENCE.md)** - Monitor device availability and status
- **[Developer Guide](docs/guides/DEVELOPER_GUIDE.md)** - Development setup and architecture

### For Agents & Technical Reference

Complete implementation details for AI agents and maintainers:

- **[Architecture](docs/specs/ARCHITECTURE.md)** - System design and components
- **[Implementation Details](docs/specs/)** - Detailed technical specifications
  - Node Tracker implementation
  - MQTT publishing system
  - Module dependencies
- **[API Reference](docs/specs/NODE_TRACKER.md)** - Python API documentation

## 🚀 Quick Start

### Installation

See the [Installation Guide](docs/guides/INSTALLATION.md) for detailed setup instructions.

```bash
# Clone and setup
git clone <repository-url>
cd MatterToMQTT
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run with default config
python3 main.py

# Run with custom config
python3 main.py /path/to/config.yaml

# Test mode (no MQTT publishing)
# Set dry_run: true in config.yaml
```

## ⚙️ Configuration

Configuration is managed via YAML (see [config.yaml](config.yaml) for all options).

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
# Create and edit custom configuration
cp config.yaml my_config.yaml
nano my_config.yaml

# Run with custom config
python3 main.py my_config.yaml
```

### Configuration File Locations

The application looks for `config.yaml` in the working directory by default.

For production deployments, recommended structure:

```
/opt/MatterToMQTT/
├── config.yaml
├── main.py
├── src/
├── docs/
└── venv/
```

## 📖 What Happens

**Matter → MQTT (Automatic)**
- Device attributes are published to MQTT topics automatically
- Example: `matter/living_room_light/on_off/state` → `true`

**MQTT → Matter (On Command)**
- Commands published to MQTT topics are sent to Matter devices
- Example: Publish to `matter/living_room_light/6/command` to control the device

**Node Monitoring (Continuous)**
- All Matter devices are discovered on startup
- Device availability is tracked with periodic polling (default: every 2 minutes)
- Signal metrics (WiFi RSSI, Thread LQI) are published
- Last-seen timestamps are updated on every device activity

## 🔍 Project Structure

```
MatterToMQTT/
├── main.py                     # Application entry point
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── src/
│   ├── matter_client.py        # Matter WebSocket client
│   ├── mqtt_bridge.py          # MQTT broker interface
│   ├── device_manager.py       # Device caching & identification
│   ├── node_tracker.py         # Device monitoring & availability
│   ├── attribute_filter.py     # Attribute whitelisting
│   └── ...
├── docs/
│   ├── guides/                 # User & developer guides
│   │   ├── INSTALLATION.md
│   │   ├── QUICK_REFERENCE.md
│   │   └── ...
│   └── specs/                  # Technical specifications
│       ├── ARCHITECTURE.md
│       ├── IMPLEMENTATION_COMPLETE.md
│       └── ...
└── tests/                      # Test suite
```

## 📝 License

This project was made mainly by Copilot. Use it at your own risk!

---

## 🙋 Need Help?

- **Getting started?** → See [Installation Guide](docs/guides/INSTALLATION.md)
- **How do I configure this?** → See [Quick Reference](docs/guides/QUICK_REFERENCE.md)
- **I want to send commands to devices** → See [Bidirectional Guide](docs/guides/BIDIRECTIONAL_GUIDE.md)
- **I'm a developer** → See [Developer Guide](docs/guides/DEVELOPER_GUIDE.md)
- **I need implementation details** → See [docs/specs/](docs/specs/)
