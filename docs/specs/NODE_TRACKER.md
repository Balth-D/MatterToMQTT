# Node Tracker - Availability Monitoring

## Overview

The Node Tracker feature automatically monitors the availability and state of all Matter devices connected to the network. It periodically polls the `get_nodes` command to maintain a real-time table of:

- **Node ID**: The unique identifier in the Matter network
- **Unique ID**: Device identifier (from Matter attribute 0/40/18)
- **Availability**: Current online/offline status
- **Last Seen**: When the device last sent an update or appeared in polling
- **Date Commissioned**: When the device was added to the Matter network
- **Last Interview**: When the device was last interviewed by the coordinator

## Configuration

### Default Settings

The node tracker is enabled by default with a 2-minute polling interval:

```yaml
# config.yaml
advanced:
  nodes_poll_interval: 120  # seconds, default 2 minutes
```

### Custom Polling Interval

To adjust the polling frequency, modify the `nodes_poll_interval` in your `config.yaml`:

```yaml
advanced:
  # Poll every 30 seconds for faster updates
  nodes_poll_interval: 30
  
  # Or poll less frequently to reduce load (every 5 minutes)
  nodes_poll_interval: 300
```

## How It Works

### 1. Initial Discovery (On Startup)

When the application starts, it receives the initial list of commissioned nodes:
- Each node's availability status is recorded
- The unique_id is cached from attribute 0/40/18
- All nodes are marked with initial timestamps

Example log output:
```
★ Nodes list received with 2 device(s) ★
  ✓ Node 16 (device: ABC123, endpoints: complex, available: true)
  ✓ Node 18 (device: XYZ789, endpoints: simple (0-1), available: false)
Ready to process attributes
```

### 2. Periodic Polling

Every N seconds (configured via `nodes_poll_interval`), the application:
1. Sends a `get_nodes` command to the Matter server
2. Receives the current state of all nodes
3. Updates the node tracker with:
   - Current availability status
   - Last interview timestamp
   - Any other attribute changes

Example log output:
```
Node status update: 2 total, 1 available
Node 18 unavailable (last seen: 2026-08-06T15:23:45.123456)
```

### 3. Attribute Update Tracking

When a device sends an attribute update:
- The node's `last_seen` timestamp is immediately updated
- This happens before the attribute is processed
- Helps track active communication even between polling cycles

## Accessing Node Information

### Via Python API

The `NodeTracker` is accessible from the application:

```python
# Get all nodes
all_nodes = app.node_tracker.get_all_nodes()
for node in all_nodes:
    print(f"Node {node.node_id}: {node.available} (last_seen: {node.last_seen})")

# Get only available nodes
available = app.node_tracker.get_available_nodes()
print(f"{len(available)} nodes online")

# Get a specific node
node = app.node_tracker.get_node(16)
if node:
    print(f"Node 16 unique_id: {node.unique_id}")
    print(f"Node 16 last_seen: {node.last_seen.isoformat()}")

# Export as dictionaries
nodes_data = app.node_tracker.get_nodes_as_dicts()
print(json.dumps(nodes_data, indent=2))
```

### Node Information Structure

Each node tracks:

```python
NodeInfo {
    node_id: int                          # Matter node ID
    unique_id: str | None                 # Device identifier (0/40/18)
    available: bool                       # Current availability status
    date_commissioned: str | None         # ISO format timestamp
    last_interview: str | None            # ISO format timestamp
    last_seen: datetime                   # When last updated locally
}
```

## Logging

The node tracker provides detailed logging at different levels:

### INFO Level
- Node discovery on startup
- Periodic polling results
- Node availability summaries

### DEBUG Level
- Individual node status updates
- Last seen timestamp updates
- Connection state changes

Example log messages:
```
# INFO: Initial discovery
Discovered new node 16: unique_id=ABC123, available=true

# INFO: Polling summary
Node status update: 2 total, 1 available

# DEBUG: Attribute update
Updated last_seen for node 16

# DEBUG: Unavailable node tracking
Node 18 unavailable (last seen: 2026-08-06T15:23:45.123456)
```

## Thread Safety

The `NodeTracker` is fully thread-safe:
- All access to node data is protected by a Lock
- Safe for concurrent access from:
  - Main event loop
  - Background polling task
  - MQTT callback threads

## Use Cases

### 1. Device Status Monitoring
Track which devices are currently online/offline and when they were last seen.

### 2. Automation Triggers
Create automations based on device availability:
- Alert when a device goes offline
- Notify when a device comes back online
- Track device responsiveness

### 3. Debugging
Identify communication issues:
- Which devices haven't been seen recently
- Devices that become unavailable repeatedly
- Coordination between polling and attribute updates

### 4. Dashboard Integration
Publish node availability to MQTT for home automation dashboards:
```
matter/node_status/16/available: true
matter/node_status/16/last_seen: 2026-08-06T15:30:22.456789
matter/node_status/18/available: false
matter/node_status/18/last_seen: 2026-08-06T15:20:10.123456
```

## Performance Considerations

### Default Settings (120s interval)
- **Low Load**: One network request every 2 minutes
- **Recommended For**: Home installations with typical internet
- **Network Impact**: Minimal

### Faster Polling (30s interval)
- **Moderate Load**: One network request every 30 seconds
- **Use Case**: Faster detection of device failures
- **Network Impact**: Increased load on Matter server

### Slow Polling (300s interval)
- **Very Low Load**: One network request every 5 minutes
- **Use Case**: Bandwidth-constrained environments
- **Tradeoff**: Slower detection of availability changes

## Troubleshooting

### Nodes Always Show as Unavailable
1. Check Matter server connectivity
2. Ensure nodes are properly commissioned
3. Verify the get_nodes command works: `matter-cli get-nodes`

### Last Seen Not Updating
1. Check polling interval setting
2. Verify attributes are being received (check logs for attribute updates)
3. Ensure no network/firewall issues blocking get_nodes command

### High Load from Polling
1. Increase `nodes_poll_interval` to reduce polling frequency
2. Monitor network traffic during polling
3. Check Matter server CPU usage

## Future Enhancements

Potential improvements for node tracking:
- MQTT publishing of node status
- Node availability alerts
- Automatic remediation actions
- Historical node state logging
- Correlation with attribute update frequency
