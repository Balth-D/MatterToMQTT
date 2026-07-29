# Quick Reference - Commands

## Topic Formats

### Full Format (explicit endpoint)
```
matter/<device_id>/<endpoint_id>/<cluster_id>/command
```

### Simple Format (endpoint defaults to 1)
```
matter/<device_id>/<cluster_id>/command
```

## Command Payloads

```json
{"command": "On", "payload": {}}
{"command": "Off", "payload": {}}
{"command": "Toggle", "payload": {}}
{"command": "MoveToLevel", "payload": {"level": 128, "transition_time": 0}}
{"command": "MoveToColor", "payload": {"color_x": 21845, "color_y": 22551, "transition_time": 0}}
```

## One-Liners

```bash
# Turn on light (full format)
mosquitto_pub -h localhost -t "matter/DEVICE/1/6/command" -m '{"command":"On","payload":{}}'

# Turn on light (simple format, endpoint defaults to 1)
mosquitto_pub -h localhost -t "matter/DEVICE/6/command" -m '{"command":"On","payload":{}}'

# Set brightness (full format)
mosquitto_pub -h localhost -t "matter/DEVICE/1/8/command" -m '{"command":"MoveToLevel","payload":{"level":200,"transition_time":0}}'

# Set brightness (simple format)
mosquitto_pub -h localhost -t "matter/DEVICE/8/command" -m '{"command":"MoveToLevel","payload":{"level":200,"transition_time":0}}'

# Subscribe to commands
mosquitto_sub -h localhost -t "matter/+/+/+/command"

# Find device IDs
python3 main.py --debug debug 2>&1 | grep "Cached identifier"
```

## Python

```python
import json, paho.mqtt.client as mqtt
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.connect("localhost")
c.publish("matter/DEVICE/1/6/command", json.dumps({"command":"On","payload":{}}))
c.disconnect()
```

## Debugging

```bash
# Debug mode
python3 main.py --debug debug

# Dry run (test without sending)
python3 main.py --dry-run --debug debug

# Run tests
python3 test_commands.py
```

## Documentation

- **BIDIRECTIONAL_GUIDE.md** - Full guide with theory and examples
- **MATTER_MQTT_README.md** - Main README
- **example_commands.py** - Working code examples
- **test_commands.py** - Unit tests

---

**For comprehensive guide, see [BIDIRECTIONAL_GUIDE.md](BIDIRECTIONAL_GUIDE.md)**
