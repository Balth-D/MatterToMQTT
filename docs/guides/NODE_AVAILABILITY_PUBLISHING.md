# Node Availability Publishing to MQTT

## Overview

The Node Tracker now publishes comprehensive node information to MQTT whenever:

1. **MQTT client connects** (including on reconnection)
2. **Periodic polling completes** (every N seconds, default 2 minutes)
3. **Initial nodes list is received** (on application startup)

This allows MQTT clients to:
- Monitor real-time node availability
- Build device status dashboards
- Create automation rules based on device state
- Detect when devices come online/offline

## MQTT Topic Structure

### Full Nodes List

**Topic:** `matter/nodes`

**Payload:** JSON array of all nodes with complete information

**Example:**
```json
[
  {
    "node_id": 16,
    "unique_id": "2FC6CAD98340F911",
    "available": true,
    "date_commissioned": "2026-05-21T09:23:18.586223",
    "last_interview": "2026-06-17T07:27:56.567092",
    "last_seen": "2026-08-06T15:30:22.123456"
  },
  {
    "node_id": 18,
    "unique_id": "97217D69269EAB77",
    "available": false,
    "date_commissioned": "2026-06-03T13:28:36.131322",
    "last_interview": "2026-06-17T07:26:47.071321",
    "last_seen": "2026-08-06T15:25:10.654321"
  }
]
```

**Retention:** Yes (retained message on broker)
**QoS:** 1 (at least once delivery)
**Update Frequency:** 
- On MQTT client connect
- Every polling interval (default: 2 minutes)
- On initial startup

### Per-Device Availability

**Topic:** `matter/{device_id}/availability`

**Payload:** JSON object with state

**Examples:**
```json
{"state":"online"}
```

```json
{"state":"offline"}
```

**Retention:** Yes (retained message on broker)
**QoS:** 1 (at least once delivery)
**Update Frequency:**
- On MQTT client connect
- Every polling interval (default: 2 minutes)
- On initial startup

## Topic Prefix Customization

The default topic prefix is `matter`. To customize, modify your config:

```yaml
mqtt:
  topic_prefix: my_matter_bridge  # Custom prefix

# Results in:
# - my_matter_bridge/nodes
# - my_matter_bridge/{device_id}/availability
```

## Publishing Schedule

### On Application Startup

```
1. Connect to MQTT broker
2. Receive initial nodes list from Matter server
3. Publish full nodes list to matter/nodes
4. Publish availability for each device
```

### During Runtime (Periodic)

Every N seconds (default 120):
```
1. Poll get_nodes from Matter server
2. Update node tracker with latest data
3. Publish full nodes list to matter/nodes
4. Publish availability for each device
```

### On MQTT Client Connect/Reconnect

Immediately:
```
1. New MQTT client connects
2. Application publishes full nodes list
3. Application publishes all device availability
```

This ensures clients always get the latest state when connecting.

## Field Descriptions

### Full Nodes List Fields

| Field | Type | Description |
|-------|------|-------------|
| `node_id` | Integer | Matter node ID (unique in network) |
| `unique_id` | String | Device identifier from attribute 0/40/18 |
| `available` | Boolean | Current availability (online: true, offline: false) |
| `date_commissioned` | ISO 8601 | When device was added to Matter network |
| `last_interview` | ISO 8601 | When device was last interviewed by coordinator |
| `last_seen` | ISO 8601 | When application last saw device activity |

### Availability State

| State | Meaning |
|-------|---------|
| `"online"` | Device is available and responsive |
| `"offline"` | Device is unavailable or not responding |

## Usage Examples

### Subscribe to All Node Updates

```bash
mosquitto_sub -h localhost -t "matter/nodes" -v
```

Output:
```
matter/nodes [{"node_id":16,"unique_id":"ABC123","available":true,...},...]
```

### Monitor Specific Device Availability

```bash
mosquitto_sub -h localhost -t "matter/light_123/availability" -v
```

Output:
```
matter/light_123/availability {"state":"online"}
matter/light_123/availability {"state":"offline"}
matter/light_123/availability {"state":"online"}
```

### Home Assistant Integration

In Home Assistant, you can use the availability information:

```yaml
mqtt:
  binary_sensor:
    - name: "Light 123 Status"
      unique_id: "light_123_status"
      state_topic: "matter/light_123/availability"
      value_template: "{{ value_json.state }}"
      payload_on: "online"
      payload_off: "offline"
      device_class: "connectivity"
```

### Node.js/JavaScript Subscription

```javascript
const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://localhost:1883');

// Subscribe to all node updates
client.subscribe('matter/nodes', (err) => {
  if (err) console.error(err);
});

client.on('message', (topic, message) => {
  if (topic === 'matter/nodes') {
    const nodes = JSON.parse(message.toString());
    console.log('Node list updated:', nodes);
    
    nodes.forEach(node => {
      console.log(`Node ${node.node_id} (${node.unique_id}): ${node.available ? 'ONLINE' : 'OFFLINE'}`);
    });
  }
});
```

### Python Monitoring

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    if msg.topic == 'matter/nodes':
        nodes = json.loads(msg.payload)
        for node in nodes:
            print(f"Node {node['node_id']}: {'✓ ONLINE' if node['available'] else '✗ OFFLINE'}")
            print(f"  Unique ID: {node['unique_id']}")
            print(f"  Last seen: {node['last_seen']}")

client = mqtt.Client()
client.on_message = on_message
client.connect('localhost', 1883)
client.subscribe('matter/nodes')
client.loop_forever()
```

## Dry Run Mode

In dry run mode, publishing is logged but not actually sent:

```bash
# With dry_run: true in config.yaml
python3 main.py config.yaml
```

Output:
```
[DRY RUN] Would publish node information to MQTT
```

## Troubleshooting

### No Messages Appearing

1. **Check MQTT connection:**
   ```bash
   mosquitto_sub -h localhost -t "matter/#" -v
   ```

2. **Verify configuration:**
   ```yaml
   advanced:
     dry_run: false  # Make sure not in dry run mode
   ```

3. **Check logs:**
   ```
   Published X nodes to matter/nodes
   ```

### Availability Not Updating

1. Verify polling is enabled:
   ```yaml
   advanced:
     nodes_poll_interval: 120  # Should not be disabled
   ```

2. Check if MQTT is connected:
   ```
   MQTT broker connected ✓
   ```

### Memory/Network Concerns

If node list is very large:

1. Increase polling interval:
   ```yaml
   advanced:
     nodes_poll_interval: 300  # Every 5 minutes instead of 2
   ```

2. Or reduce frequency of network checks:
   ```yaml
   advanced:
     nodes_poll_interval: 600  # Every 10 minutes
   ```

## Implementation Details

### Publishing Flow

```
Event Trigger
    ↓
_publish_node_information()
    ├─→ Get all nodes from NodeTracker
    ├─→ Publish full list to matter/nodes (retained)
    └─→ For each node:
        ├─→ Get device identifier
        ├─→ Publish availability to matter/{device_id}/availability (retained)
        └─→ Log the update
```

### Connection Handling

When MQTT client connects or reconnects:
1. `on_connect` callback is triggered
2. `_on_mqtt_client_connect()` is called
3. `_publish_node_information()` publishes all current state
4. Any subscribed MQTT clients receive the updates

### Integration Points

- **MQTTBridge:** Added `on_client_connect()` callback support
- **MatterToMQTTApp:** Added node publishing methods
- **NodeTracker:** Existing methods used for data retrieval

## Performance Impact

### Network Impact
- Full node list: ~500 bytes per node (depends on unique_id length)
- Per-device availability: ~30 bytes per device
- Polling frequency: Every 2 minutes (configurable)

### Example Calculations
- 10 devices every 2 minutes = ~100 KB/hour of MQTT traffic
- 100 devices every 2 minutes = ~1 MB/hour of MQTT traffic

### Optimization Tips

1. **Increase polling interval** if traffic is high:
   ```yaml
   nodes_poll_interval: 300  # 5 minutes instead of 2
   ```

2. **Use topic filters** in MQTT clients:
   ```bash
   # Only specific devices
   mosquitto_sub -t "matter/light_*/availability"
   ```

3. **Process in batches** in consumers:
   ```python
   # Batch process instead of per-message
   ```

## Future Enhancements

Potential additions:
- Configurable publish topics
- Node count summary
- Device type information
- Signal strength/latency metrics
- Historical trend publishing
