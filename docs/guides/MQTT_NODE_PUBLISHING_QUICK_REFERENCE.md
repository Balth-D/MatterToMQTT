# MQTT Node Publishing - Quick Reference

## What Gets Published

### 1. Full Nodes List
**Topic:** `matter/nodes`
**When:** On startup, client connect, every poll cycle
**Content:** JSON array of all nodes with full details

```json
[
  {
    "node_id": 16,
    "unique_id": "ABC123",
    "available": true,
    "last_seen": "2026-08-06T15:30:22.123456",
    "date_commissioned": "2026-05-21T09:23:18.586223",
    "last_interview": "2026-06-17T07:27:56.567092"
  }
]
```

### 2. Per-Device Availability
**Topic:** `matter/{device_id}/availability`
**When:** On startup, client connect, every poll cycle
**Content:** Simple state indicator

```json
{"state":"online"}
```

or

```json
{"state":"offline"}
```

## Subscribe Examples

```bash
# Watch all nodes
mosquitto_sub -h localhost -t "matter/nodes" -v

# Watch specific device
mosquitto_sub -h localhost -t "matter/light_123/availability" -v

# Watch all device availability
mosquitto_sub -h localhost -t "matter/+/availability" -v
```

## Configuration

Default settings (no changes needed):
```yaml
mqtt:
  topic_prefix: matter  # Where matter/nodes and matter/{id}/availability are published

advanced:
  nodes_poll_interval: 120  # Publish every 2 minutes
```

Customize topic prefix:
```yaml
mqtt:
  topic_prefix: home/matter
  # Results in: home/matter/nodes, home/matter/{id}/availability
```

Change polling frequency:
```yaml
advanced:
  nodes_poll_interval: 60   # Publish every minute (faster)
  nodes_poll_interval: 300  # Publish every 5 minutes (slower)
```

## Publishing Schedule

| Event | Action |
|-------|--------|
| **Application startup** | Publish full nodes list + all availability |
| **Every 2 minutes** (default) | Publish full nodes list + all availability |
| **MQTT client connects** | Immediately publish full nodes list + all availability |
| **Attribute update** | Last_seen timestamp updated (next poll publishes) |

## Usage Patterns

### Monitor Node Status
```javascript
client.subscribe('matter/nodes');
client.on('message', (topic, msg) => {
  const nodes = JSON.parse(msg);
  nodes.forEach(n => {
    console.log(`Node ${n.node_id}: ${n.available ? 'ONLINE' : 'OFFLINE'}`);
  });
});
```

### Detect When Device Goes Down
```bash
mosquitto_sub -t "matter/thermostat_01/availability" -v | while read line; do
  if echo "$line" | grep -q '"offline"'; then
    echo "Alert: Thermostat is offline!"
  fi
done
```

### Home Assistant Availability
```yaml
# In configuration.yaml
mqtt:
  binary_sensor:
    - name: "Device Status"
      state_topic: "matter/device_01/availability"
      value_template: "{{ value_json.state }}"
      payload_on: "online"
      payload_off: "offline"
```

## Logs to Watch For

**Startup:**
```
★ Nodes list received with 2 device(s) ★
Ready to process attributes
Published 2 nodes to matter/nodes
Published availability for device ABC123 (node 16): online
```

**Polling:**
```
Node status update: 2 total, 1 available
Published 2 nodes to matter/nodes
Published availability for device ABC123 (node 16): online
```

**MQTT Connect:**
```
MQTT client connected, publishing node information
Published 2 nodes to matter/nodes
```

## Field Reference

| Field | Example | Description |
|-------|---------|-------------|
| `node_id` | `16` | Matter network node ID |
| `unique_id` | `"ABC123"` | Device identifier |
| `available` | `true` | Online/offline status |
| `last_seen` | `"2026-08-06T15:30:22"` | Last activity timestamp |
| `date_commissioned` | `"2026-05-21T09:23:18"` | When added to network |
| `last_interview` | `"2026-06-17T07:27:56"` | Last coordinator check |

## Customization by Prefix

Default behavior:
```yaml
mqtt:
  topic_prefix: matter
# Topics: matter/nodes, matter/device_id/availability
```

Custom prefix for multiple bridges:
```yaml
mqtt:
  topic_prefix: home/office  # Multiple bridges in one home
# Topics: home/office/nodes, home/office/device_id/availability
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No messages on MQTT | Check `dry_run: false` in config |
| Messages only on connect | Polling might be disabled |
| Too frequent messages | Increase `nodes_poll_interval` |
| Missing devices | Check matter server connection |

## MQTT Broker Settings

These topics use:
- **Retention:** Enabled (messages persist after disconnect)
- **QoS:** Level 1 (at least once delivery)
- **Persistence:** Survives broker restart

Perfect for dashboards and status displays!
