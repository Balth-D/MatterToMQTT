# Matter WebSocket to MQTT Bridge

This script connects to a [python-matter-server](https://github.com/matter-js/python-matter-server) WebSocket endpoint and forwards attribute updates to an MQTT broker with Zigbee2MQTT-like topic structure.

## What the script does

- Connects to a Matter server WebSocket (default: `ws://127.0.0.1:5580/ws`)
- Subscribes to live attribute updates
- Caches device identifiers from the 0/40/18 attribute (used in MQTT topics instead of node IDs)
- Filters attributes based on an optional JSON configuration file
- Publishes attribute updates to MQTT with human-readable cluster/attribute names
- Supports dry-run mode for testing without sending to MQTT
- Provides configurable debug logging levels

## Installation

1. Create and activate a Python environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Command-line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--url-ws` | `ws://127.0.0.1:5580/ws` | Matter server WebSocket URL |
| `--url-mqtt` | `mqtt://127.0.0.1:1883` | MQTT server URL |
| `--mqtt-topic-prefix` | `matter` | MQTT topic prefix |
| `--mqtt-user` | None | MQTT username (optional) |
| `--mqtt-password` | None | MQTT password (optional) |
| `--filter` | None | JSON file with allowed clusters/attributes (optional) |
| `--debug` | `info` | Debug level: `debug`, `info`, `warning`, `error` |
| `--dry-run` | False | Dry run mode - don't send to MQTT, just log |
| `--reconnect-delay` | `5.0` | Seconds between reconnect attempts |

## Usage Examples

### Basic usage (publish all attributes)
```bash
python3 matter_ws_attr_to_mqtt.py
```

### With MQTT authentication
```bash
python3 matter_ws_attr_to_mqtt.py \
  --url-mqtt mqtt://192.168.1.100:1883 \
  --mqtt-user myuser \
  --mqtt-password mypass
```

### With attribute filter
```bash
python3 matter_ws_attr_to_mqtt.py \
  --filter attributes.json
```

### Dry run with debug logging
```bash
python3 matter_ws_attr_to_mqtt.py \
  --dry-run \
  --debug debug
```

### Full configuration
```bash
python3 matter_ws_attr_to_mqtt.py \
  --url-ws ws://192.168.1.50:5580/ws \
  --url-mqtt mqtt://192.168.1.100:1883 \
  --mqtt-user homeassistant \
  --mqtt-password secret \
  --mqtt-topic-prefix home/matter \
  --filter attributes.json \
  --debug info
```

## MQTT Topic Structure

Topics follow the Zigbee2MQTT format:
```
matter/<device_identifier>/<endpoint_id>/<cluster_name>/<attribute_name>
```

**Example topics:**
- `matter/108ECBDA7AA92CDD/1/on_off/state`
- `matter/108ECBDA7AA92CDD/1/temperature/measured_value`
- `matter/108ECBDA7AA92CDD/1/electrical_measurement/active_power`

## Device Identifier Caching

The script automatically detects device identifiers from the Matter attribute at path `0/40/18` (Endpoint 0, Cluster 0x0028, Attribute 0x0012). This happens once per device when first encountered. If a device doesn't have this attribute, the node ID is used as a fallback.

## Filter File Format

Create a JSON file to specify which clusters and attributes to publish. Only attributes in this file will be forwarded to MQTT.

**Example:** `attributes.json`
```json
{
  "0x0090": {
    "name": "electrical_measurement",
    "attributes": {
      "0x0000": "power_mode",
      "0x0004": "voltage",
      "0x0008": "active_power",
      "0x000B": "rms_voltage",
      "0x000D": "rms_power"
    }
  },
  "0x0400": {
    "name": "illuminance",
    "attributes": {
      "0x0000": "measured_value"
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

### Filter File Structure

- **Top level**: Cluster ID (hexadecimal or decimal)
  - `name`: Human-readable cluster name (used in MQTT topics)
  - `attributes`: Dictionary of allowed attributes
    - **Key**: Attribute ID (hexadecimal or decimal)
    - **Value**: Human-readable attribute name (used in MQTT topics)

## Debug Levels

- **`debug`**: Verbose output including filtered-out attributes and detailed attribute updates
- **`info`**: Normal operation logging (default)
- **`warning`**: Only warnings and errors
- **`error`**: Only error messages

## Dry Run Mode

Use `--dry-run` to test your configuration without sending messages to MQTT:
```bash
python3 matter_ws_attr_to_mqtt.py \
  --filter attributes.json \
  --dry-run \
  --debug info
```

Output will show `[DRY RUN] Would publish to ...` instead of actually publishing.

## MQTT Message Format

Each published message is a JSON object:
```json
{
  "value": 25.5,
  "timestamp": "2026-07-10T14:30:45.123Z"
}
```
