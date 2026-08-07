# Node Tracker Implementation Summary

## 🎯 Feature Implementation Complete

I have successfully implemented the Node Tracker feature for MatterToMQTT. This feature periodically polls the Matter server's `get_nodes` command to maintain an up-to-date table of all connected devices and their availability status.

## 📋 What Was Implemented

### 1. **NodeTracker Module** (`src/node_tracker.py`)
A new module that manages node state with two main classes:

#### `NodeInfo` Class
Represents a single Matter device with:
- `node_id`: The unique identifier in the Matter network
- `unique_id`: Device identifier (from attribute 0/40/18)
- `available`: Current availability status (online/offline)
- `date_commissioned`: When device was added to network
- `last_interview`: Last communication timestamp from Matter
- `last_seen`: Local timestamp when we last saw any update from this device

Methods:
- `update_availability()`: Updates status and `last_seen` timestamp
- `update_last_seen()`: Updates timestamp without changing availability
- `to_dict()`: Serializes node info to dictionary

#### `NodeTracker` Class
Thread-safe manager for all nodes with methods:
- `update_from_nodes_list()`: Populates/updates nodes from `get_nodes` response
- `mark_node_attribute_update()`: Called when device sends attribute update
- `get_node(node_id)`: Get specific node info
- `get_all_nodes()`: Get all tracked nodes
- `get_available_nodes()`: Get only online nodes
- `get_unavailable_nodes()`: Get only offline nodes
- `get_nodes_as_dicts()`: Export all nodes as dictionaries

### 2. **Configuration Updates** (`src/config.py` & `config.yaml`)
Added new configuration option:

```yaml
advanced:
  nodes_poll_interval: 120  # seconds (default: 2 minutes)
```

This controls how often the application polls `get_nodes` command.

### 3. **Matter Client Enhancement** (`src/matter_client.py`)
Added async method `get_nodes()` that:
- Sends `get_nodes` command to Matter server
- Waits for response with proper message ID matching
- Returns list of node data or None on error
- Handles timeouts gracefully (max 3 attempts, 5s each)

### 4. **Application Integration** (`main.py`)
Modified the main application to:
- Initialize NodeTracker in `__init__`
- Run periodic polling in parallel with message consumption
- Update NodeTracker when nodes list is received
- Mark nodes as "seen" when they send attribute updates
- Added `_poll_nodes_periodically()` method that:
  - Respects the configured polling interval
  - Logs node status summaries
  - Handles errors gracefully
  - Stops cleanly on shutdown

### 5. **Documentation** (`docs/NODE_TRACKER.md`)
Comprehensive documentation including:
- Feature overview and configuration
- How the system works internally
- API usage examples
- Logging details
- Performance considerations
- Troubleshooting guide

## 🚀 How It Works

### Startup Flow
1. Application connects to Matter server
2. Receives initial list of all commissioned nodes
3. NodeTracker caches: node_id, unique_id, availability status, dates
4. Logs all discovered nodes with their availability

### Runtime Flow
1. **Attribute Updates**: When a device sends an attribute update:
   - NodeTracker marks that node's `last_seen` timestamp
   - Attribute is processed normally

2. **Periodic Polling**: Every N seconds (configurable):
   - Application sends `get_nodes` command
   - Receives current state of all nodes
   - Updates NodeTracker with latest availability
   - Logs summary (total nodes, available nodes)

3. **Continuous Availability Tracking**:
   - `last_seen` updates on every attribute update
   - `last_seen` also updates on polling cycles
   - Provides complete visibility into device communication

## 📊 Key Features

✅ **Automatic Node Discovery**: All nodes on startup
✅ **Periodic Polling**: Configurable interval (default: 2 minutes)
✅ **Dual-Source Updates**: From polling AND attribute updates
✅ **Thread-Safe**: All node data access protected by Lock
✅ **Graceful Shutdown**: Polling stops cleanly on exit
✅ **Detailed Logging**: INFO and DEBUG level logging
✅ **Error Handling**: Timeouts and connection errors handled
✅ **Easy Access**: Simple API to query node status

## 🔧 Configuration

### Default (Recommended)
```yaml
advanced:
  nodes_poll_interval: 120  # 2 minutes
```

### Fast Polling
```yaml
advanced:
  nodes_poll_interval: 30   # 30 seconds (faster detection)
```

### Slow Polling
```yaml
advanced:
  nodes_poll_interval: 300  # 5 minutes (less network load)
```

## 📝 Example Usage

```python
# Get all nodes
all_nodes = app.node_tracker.get_all_nodes()

# Check specific node
node = app.node_tracker.get_node(16)
if node:
    print(f"Node 16 is {'available' if node.available else 'unavailable'}")
    print(f"Last seen: {node.last_seen}")
    print(f"Unique ID: {node.unique_id}")

# Get availability summary
available = app.node_tracker.get_available_nodes()
print(f"{len(available)} of {len(all_nodes)} nodes are online")

# Export as JSON
import json
data = app.node_tracker.get_nodes_as_dicts()
print(json.dumps(data, indent=2))
```

## 📊 Sample Response Data

The node tracker processes data from the Matter `get_nodes` response:

```json
{
  "node_id": 16,
  "unique_id": "2FC6CAD98340F911",
  "available": true,
  "date_commissioned": "2026-05-21T09:23:18.586223",
  "last_interview": "2026-06-17T07:27:56.567092",
  "last_seen": "2026-08-06T15:30:22.123456"
}
```

## 🔍 Logging Examples

### On Startup
```
★ Nodes list received with 2 device(s) ★
  ✓ Node 16 (device: ABC123, endpoints: complex, available: true)
  ✓ Node 18 (device: XYZ789, endpoints: simple (0-1), available: false)
Ready to process attributes
```

### During Polling
```
Node status update: 2 total, 1 available
Node 18 unavailable (last seen: 2026-08-06T15:23:45.123456)
```

### On Attribute Updates
```
Updated last_seen for node 16
```

## 🧪 Testing

All syntax has been verified:
✅ Python syntax check passed for all files
✅ Module imports verified
✅ All dependencies satisfied

## 📚 Files Modified

1. **src/node_tracker.py** - NEW (180 lines)
   - NodeInfo class
   - NodeTracker class
   - Full thread-safety and error handling

2. **src/config.py** - MODIFIED
   - Added `nodes_poll_interval` to DEFAULT_CONFIG
   - Added field to Config dataclass
   - Updated from_yaml() to extract new setting

3. **src/matter_client.py** - MODIFIED
   - Added async `get_nodes()` method
   - Handles response parsing and timeouts

4. **main.py** - MODIFIED
   - Added NodeTracker import and initialization
   - Modified run() to run polling in parallel
   - Updated _on_nodes_list() to update tracker
   - Updated _on_attribute_update() to mark nodes as seen
   - Added _poll_nodes_periodically() method

5. **config.yaml** - MODIFIED
   - Added `nodes_poll_interval` configuration option

6. **docs/NODE_TRACKER.md** - NEW
   - Complete feature documentation
   - Configuration guide
   - API reference
   - Troubleshooting guide

## ✨ Next Steps

The feature is ready to use! To get started:

1. **Configure the polling interval** (optional - 2 min default):
   ```yaml
   advanced:
     nodes_poll_interval: 120  # Adjust as needed
   ```

2. **Run the application** as usual:
   ```bash
   python3 main.py config.yaml
   ```

3. **Monitor the logs** to see node discovery and polling:
   ```
   ★ Nodes list received with X device(s) ★
   Node status update: X total, Y available
   ```

4. **Access node information** programmatically via `app.node_tracker`

## 🎓 Additional Documentation

See [docs/NODE_TRACKER.md](docs/NODE_TRACKER.md) for:
- Detailed feature overview
- Configuration options
- API usage examples
- Performance tuning
- Troubleshooting guide
