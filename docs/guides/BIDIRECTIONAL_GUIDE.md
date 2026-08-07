# Bidirectional Communication Guide

## Overview

The Matter-to-MQTT bridge now supports **full duplex communication**:
- **Download (Matter → MQTT)**: Device attribute updates are published to MQTT
- **Upload (MQTT → Matter)**: Commands published to MQTT topics are sent to devices

## MQTT Command Topics

Commands are sent to topics with the following structure:

### Full Format (with endpoint)
```
matter/<device_id>/<endpoint_id>/<cluster_id>/command
```

### Simple Format (endpoint defaults to 1)
```
matter/<device_id>/<cluster_id>/command
```

Endpoint automatically defaults to `1`. This format is recommended for single-endpoint devices (endpoints 0 and 1 only) to match the download topic structure. See [Single Endpoint Device Handling](#single-endpoint-device-handling) below for details.

### Topic Structure

| Part | Description | Example |
|------|-------------|---------|
| `matter` | MQTT prefix | Configurable via `--mqtt-topic-prefix` |
| `<device_id>` | Device identifier | `108ECBDA7AA92CDD` or node ID |
| `<endpoint_id>` | Matter endpoint | `1`, `2`, etc. |
| `<cluster_id>` | Matter cluster ID | `6` (on/off), `8` (level), etc. |
| `command` | Literal word | Always `command` |

### Topic Examples

```
matter/108ECBDA7AA92CDD/1/6/command          # On/off cluster
matter/LivingRoom_Light/1/8/command          # Level control cluster
matter/Plug_Device/1/6/command               # Plug on/off
```

## Command Payload Format

The MQTT payload must be a JSON object with the following structure:

```json
{
  "command": "CommandName",
  "payload": {}
}
```

### Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command` | string | Yes | The command name (e.g., "On", "Off", "MoveToLevel") |
| `payload` | object | Yes | Command-specific parameters (empty `{}` for simple commands) |

## Usage Examples

### Example 1: Turn On a Light

**Topic:**
```
matter/108ECBDA7AA92CDD/1/6/command
```

**Payload:**
```json
{
  "command": "On",
  "payload": {}
}
```

### Example 2: Turn Off a Light

**Topic:**
```
matter/108ECBDA7AA92CDD/1/6/command
```

**Payload:**
```json
{
  "command": "Off",
  "payload": {}
}
```

### Example 3: Set Light Level (Level Control)

**Topic:**
```
matter/108ECBDA7AA92CDD/1/8/command
```

**Payload:**
```json
{
  "command": "MoveToLevel",
  "payload": {
    "level": 128,
    "transition_time": 0
  }
}
```

### Example 4: Toggle Light

**Topic:**
```
matter/108ECBDA7AA92CDD/1/6/command
```

**Payload:**
```json
{
  "command": "Toggle",
  "payload": {}
}
```

## Common Commands

### On/Off Cluster (0x0006)

```json
{ "command": "On", "payload": {} }
{ "command": "Off", "payload": {} }
{ "command": "Toggle", "payload": {} }
```

### Level Control Cluster (0x0008)

```json
{
  "command": "MoveToLevel",
  "payload": {
    "level": 254,
    "transition_time": 0
  }
}
```

### Color Control Cluster (0x0300)

```json
{
  "command": "MoveToColor",
  "payload": {
    "color_x": 21845,
    "color_y": 22551,
    "transition_time": 0
  }
}
```

## MQTT Publishing Tools

### Using `mosquitto_pub`

```bash
# Turn on a light
mosquitto_pub -h localhost \
  -t "matter/108ECBDA7AA92CDD/1/6/command" \
  -m '{"command":"On","payload":{}}'

# Set brightness to 50%
mosquitto_pub -h localhost \
  -t "matter/108ECBDA7AA92CDD/1/8/command" \
  -m '{"command":"MoveToLevel","payload":{"level":127,"transition_time":0}}'
```

### Using Python

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)

# Send command
command = {
    "command": "On",
    "payload": {}
}
topic = "matter/108ECBDA7AA92CDD/1/6/command"
client.publish(topic, json.dumps(command))
client.disconnect()
```

### Using Node.js

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('mqtt://localhost');
const topic = 'matter/108ECBDA7AA92CDD/1/6/command';
const command = JSON.stringify({
  command: 'On',
  payload: {}
});

client.publish(topic, command);
client.end();
```

### Using Home Assistant

In `automations.yaml`:

```yaml
alias: Turn on light via MQTT
trigger:
  platform: time
  at: "19:00:00"
action:
  service: mqtt.publish
  data:
    topic: matter/108ECBDA7AA92CDD/1/6/command
    payload: '{"command":"On","payload":{}}'
```

Or in a template:

```jinja2
{% set topic = "matter/108ECBDA7AA92CDD/1/6/command" %}
{% set command = {"command": "On", "payload": {}} %}
{{ topic }}: {{ command | tojson }}
```

## Device Identifier Resolution

### How it Works

1. When the bridge starts, it caches device identifiers from the Matter attribute `0/40/18`
2. This creates a mapping: `node_id` ↔ `device_id` (e.g., "1234" ↔ "108ECBDA7AA92CDD")
3. When a command arrives via MQTT, the topic contains the `device_id`
4. The bridge looks up the corresponding `node_id` and sends the command

### If Device ID is Unknown

If you publish to a topic with an unknown device ID:

```
matter/UnknownDevice/1/6/command
```

The bridge will log a warning:

```
WARNING: Unknown device ID: UnknownDevice. Cannot route command from topic matter/UnknownDevice/1/6/command
```

**Solution:** Use the device identifier that was cached at startup (shown in logs), or use the node ID directly if device caching is not available.

## Debugging Commands

### Enable Debug Logging

```bash
python3 main.py --debug debug
```

You'll see:

```
DEBUG: Received MQTT message on matter/108ECBDA7AA92CDD/1/6/command: {"command":"On","payload":{}}
DEBUG: Parsed command: node_id=1234, endpoint=1, cluster=6, command=On
Sent command to device: node_id=1234, endpoint=1, cluster=6, command=On
```

### Dry Run Mode

Test commands without sending them to the device:

```bash
python3 main.py --dry-run --debug debug
```

Output:

```
[DRY RUN] Would send command: node_id=1234, endpoint=1, cluster=6, command=On
```

## Error Handling

### Invalid Command Topic Format

Topic must match: `prefix/<device_id>/<endpoint_id>/<cluster_id>/command`

Invalid topics are ignored:
- `matter/device/command` ❌ (missing endpoint/cluster)
- `matter/device/1/6` ❌ (missing `/command`)
- `matter/device/abc/6/command` ❌ (endpoint must be numeric)

### Invalid Payload Format

Payload must be valid JSON:

```
ERROR: Failed to parse command payload as JSON
```

Payload must have "command" field:

```
WARNING: Command payload missing 'command' field
```

### Unknown Device ID

Device ID doesn't match any cached identifier:

```
WARNING: Unknown device ID: SomeDevice. Cannot route command from topic...
```

## Architecture

### Command Flow

```
MQTT Broker
    │
    ├── Publish to: matter/device/1/6/command
    │   Payload: {"command":"On","payload":{}}
    │
    ▼
MQTTBridge
    │
    ├── on_message callback
    │   └── topic + payload
    │
    ▼
MatterToMQTTApp._on_mqtt_message()
    │
    ├── CommandRouter.parse_mqtt_command()
    │   ├── Parse topic
    │   ├── Parse payload
    │   ├── Lookup node_id from device_id
    │   └── Create MQTTCommand
    │
    ▼
MatterToMQTTApp._send_command_to_device()
    │
    ├── Check dry-run mode
    │
    ▼
MatterClient.send_device_command()
    │
    ├── Create device_command message
    ├── Send via WebSocket
    │
    ▼
Matter Server
    │
    └── Execute command on device
```

### Code Components

- **`command_handler.py`** - Parsing and routing
  - `MQTTCommand` - Data class for commands
  - `CommandTopicParser` - Parse topics and payloads
  - `CommandRouter` - Route commands to devices

- **`mqtt_bridge.py`** - MQTT communication
  - `subscribe()` - Listen for commands
  - `on_message` callback - Handle incoming messages

- **`matter_client.py`** - Matter communication
  - `send_device_command()` - Send commands to Matter server

- **`device_manager.py`** - Device tracking
  - `get_node_id_by_device_identifier()` - Reverse lookup

- **`main.py`** - Orchestration
  - `_on_mqtt_message()` - Handle MQTT messages
  - `_send_command_to_device()` - Send to Matter

## Limitations

1. **No attribute writing** - Only commands are supported, not attribute writes
2. **No response handling** - Commands are sent but responses are not published back to MQTT
3. **No validation** - Command names and payloads are not validated against the device
4. **Fire and forget** - No confirmation that the command executed successfully

## Future Enhancements

- [ ] Publish command responses to MQTT
- [ ] Validate commands against attribute definitions
- [ ] Support attribute writes (not just commands)
- [ ] Publish command status/confirmation
- [ ] Command queuing and retry logic
- [ ] Rate limiting for rapid commands
- [ ] Command history/logging

## Troubleshooting

### Commands Not Being Sent

**Check 1: Verify MQTT subscription**
```bash
mosquitto_sub -h localhost -t "matter/+/+/+/command"
```
Then publish a test command and see if it appears.

**Check 2: Check device identifier**
Look at startup logs:
```
Cached identifier for node 1234: 108ECBDA7AA92CDD
```
Use the identifier in the topic.

**Check 3: Enable debug logging**
```bash
python3 main.py --debug debug
```
Look for parsing and routing messages.

### "Unknown device ID" Error

Verify the device identifier is correct. Check the logs for what identifiers were cached:

```bash
python3 main.py --debug debug 2>&1 | grep "Cached identifier"
```

### Payload Not Recognized

Ensure JSON is valid:
```bash
echo '{"command":"On","payload":{}}' | python3 -m json.tool
```

Ensure the command name matches what the device expects (e.g., "On" not "ON").

## Single Endpoint Device Handling

### Device Classification

The bridge classifies devices into two types:

**Simple Devices** (Endpoints 0 and 1 only):
```python
# Detected at startup
endpoints = {0, 1}
simple_endpoints = endpoints <= {0, 1}  # True

# Examples: Lights, plugs, simple sensors
```

**Complex Devices** (3+ endpoints):
```python
endpoints = {0, 1, 2, 3}
simple_endpoints = endpoints <= {0, 1}  # False

# Examples: Bridges, multi-output controllers
```

### Download Behavior (Matter → MQTT)

**Simple devices** - endpoint **omitted**:
```
matter/light_123/on_off/state              # No endpoint
matter/light_123/level_control/level       # No endpoint
```

**Complex devices** - endpoint **included**:
```
matter/bridge/1/on_off/state               # Endpoint 1
matter/bridge/2/temperature/measured_value # Endpoint 2
```

### Upload Behavior (MQTT → Matter) - Both Formats Supported

Both formats work for flexibility:

**Full format (explicit endpoint):**
```
matter/device/1/6/command
```

**Simple format (defaults to endpoint 1):**
```
matter/device/6/command
```

Both parse to the same command: `endpoint=1, cluster=6`

### Full Duplex Consistency

| Device Type | Download Topic | Upload Topic | Notes |
|---|---|---|---|
| Simple (1 endpoint) | `matter/light/on_off/state` | `matter/light/6/command` | Endpoint omitted both directions |
| Complex (N endpoints) | `matter/bridge/1/on_off/state` | `matter/bridge/1/6/command` | Endpoint explicit both directions |

### Why Endpoint 1?

In Matter:
- Endpoint 0 = Root (device info)
- Endpoint 1 = First functional endpoint (lights, switches, etc.)

Most single-endpoint devices use endpoint 1, so it's the default when omitted.

### Override Default Endpoint

If your device uses a different endpoint, specify it explicitly:

```bash
# Device uses endpoint 2
mosquitto_pub -t "matter/device/2/6/command" \
  -m '{"command":"On","payload":{}}'
```

### Debug: See Device Classification

```bash
python3 main.py --debug debug 2>&1 | grep -i "endpoint"
```

Output:
```
Device 1234 has only endpoints 0 and 1 (simple device)
Device 5678 has multiple endpoints (complex device)
Parsed command: endpoint=1, cluster=6 (auto-defaulted)
```

## See Also

- **QUICK_REFERENCE.md** - Command copy-paste examples
- **MATTER_MQTT_README.md** - Overall system documentation
- **ARCHITECTURE.md** - System architecture
