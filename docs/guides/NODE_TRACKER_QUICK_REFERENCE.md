# Node Tracker - Quick Reference

## ⚡ Quick Start

The Node Tracker is **enabled by default** and requires **no configuration** to use. It will:
- Automatically discover all commissioned nodes on startup
- Poll node availability every 2 minutes (configurable)
- Track when each node was last seen (from polling or attribute updates)

## 🎯 What Gets Tracked

For each node, the tracker maintains:
| Field | Source | Updates |
|-------|--------|---------|
| `node_id` | Initial discovery | Once |
| `unique_id` | Attribute 0/40/18 | Initial + Polling |
| `available` | Polling only | Every poll interval |
| `last_seen` | Polling + Attributes | Every poll or attribute update |
| `date_commissioned` | Initial discovery | Once |
| `last_interview` | Polling | Every poll interval |

## ⚙️ Configuration

### Default
```yaml
advanced:
  nodes_poll_interval: 120  # 2 minutes
```

### Change Polling Interval
```yaml
advanced:
  nodes_poll_interval: 60   # 1 minute (more frequent)
  # OR
  nodes_poll_interval: 300  # 5 minutes (less frequent)
```

## 📊 Usage Examples

### Get Node Status
```python
node = app.node_tracker.get_node(16)
if node:
    print(f"Available: {node.available}")
    print(f"Last seen: {node.last_seen}")
    print(f"ID: {node.unique_id}")
```

### Get All Nodes
```python
all_nodes = app.node_tracker.get_all_nodes()
for node in all_nodes:
    status = "🟢 Online" if node.available else "🔴 Offline"
    print(f"Node {node.node_id}: {status} ({node.last_seen})")
```

### Get Available Nodes Only
```python
online = app.node_tracker.get_available_nodes()
print(f"{len(online)} nodes are online")
```

### Export as JSON
```python
import json
nodes = app.node_tracker.get_nodes_as_dicts()
print(json.dumps(nodes, indent=2))
```

## 📝 Log Output

### Startup Discovery
```
★ Nodes list received with 2 device(s) ★
  ✓ Node 16 (device: ABC123, endpoints: complex, available: true)
  ✓ Node 18 (device: XYZ789, endpoints: simple (0-1), available: false)
```

### Periodic Polling
```
Node status update: 2 total, 1 available
Node 18 unavailable (last seen: 2026-08-06T15:23:45.123456)
```

### Attribute Updates
```
Updated last_seen for node 16
```

## 🔄 Update Flow

```
                 ┌─────────────────────┐
                 │  Application Start  │
                 └──────────┬──────────┘
                            │
                   ┌────────▼────────┐
                   │ Initial Nodes   │
                   │ Discovery       │
                   │ (get_nodes)     │
                   └────────┬────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    ┌────────────┐   ┌────────────┐    ┌────────────┐
    │ Attribute  │   │ Polling    │    │ NodeTracker│
    │ Updates    │   │ (Every Ns) │    │ Updated    │
    │ Mark Seen  │   │ Mark Seen  │    │            │
    │ + Update   │   │ + Update   │    │            │
    │ Availability   │ Availability   │ Provides   │
    └────────────┘   └────────────┘    └────────────┘
```

## 🚨 Common Issues

| Problem | Solution |
|---------|----------|
| Nodes show as unavailable | Check Matter server connection |
| Last seen not updating | Ensure polling interval is configured |
| High network load | Increase `nodes_poll_interval` value |
| Missing nodes | Verify nodes are commissioned in Matter |

## 🔧 Performance Tips

| Use Case | Interval | Notes |
|----------|----------|-------|
| Development/Testing | 30s | Fast feedback |
| Home Installation | 120s | Default, balanced |
| Large Installation | 300s | Reduce load |
| High Reliability | 60s | Faster detection |

## 📚 Full Documentation

For more details, see:
- [docs/NODE_TRACKER.md](docs/NODE_TRACKER.md) - Complete feature documentation
- [NODE_TRACKER_IMPLEMENTATION.md](NODE_TRACKER_IMPLEMENTATION.md) - Implementation details

## ✅ Verification

To verify Node Tracker is working:

1. **Check logs on startup** - Should see "Nodes list received with X device(s)"
2. **Monitor polling logs** - Should see "Node status update" every N seconds
3. **Look for last_seen updates** - Every attribute or polling cycle
4. **Test availability detection** - Turn off a device and watch status change on next poll

## 🎯 Key Features

✨ Automatic node discovery
✨ Periodic polling (configurable interval)
✨ Dual-source updates (polling + attributes)
✨ Last seen tracking
✨ Availability status
✨ Thread-safe access
✨ Detailed logging
✨ Simple Python API
