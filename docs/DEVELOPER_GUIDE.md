# Quick Developer Guide

## Getting Started

### Installation
```bash
cd /home/bdlr2/Downloads/MatterToMQTT
pip install -r requirements.txt
```

### Running the Application
```bash
python3 main.py --help
python3 main.py
python3 main.py --dry-run --debug debug
```

## Project Structure

### Modules Breakdown

| Module | Lines | Purpose |
|--------|-------|---------|
| `config.py` | ~71 | Configuration and CLI parsing |
| `logger_config.py` | ~24 | Logging setup |
| `utils.py` | ~51 | Shared utilities |
| `attribute_filter.py` | ~96 | Filtering logic |
| `device_manager.py` | ~55 | Device state |
| `mqtt_bridge.py` | ~81 | MQTT client |
| `matter_client.py` | ~165 | WebSocket client |
| `main.py` | ~145 | App orchestrator |

**Total**: ~688 lines of clean, organized code

## Common Tasks

### How to Add a New CLI Argument
1. Edit `config.py` - Add field to `Config` dataclass
2. Edit `config.py` - Add argument to `build_parser()`
3. Edit `main.py` or relevant module - Use the new config value

### How to Change MQTT Publishing Logic
1. Edit `main.py` - Modify `_on_attribute_update()` method
2. Or extend `MQTTBridge` class for new publishing strategies

### How to Add Device-Specific Handling
1. Edit `device_manager.py` - Add methods to track device state
2. Edit `main.py` - Use in `_on_nodes_list()` or `_on_attribute_update()`

### How to Add New Filtering Criteria
1. Edit `attribute_filter.py` - Add method to `AttributeFilter` class
2. Edit `main.py` - Call method in `_on_attribute_update()`

### How to Test a Module in Isolation

```python
# Test AttributeFilter
from attribute_filter import AttributeFilter

filter = AttributeFilter.from_file("attributes_filter_example.json")
print(filter.is_allowed("144", "8"))  # Check if allowed
print(filter.get_cluster_name("144"))  # Get cluster name
```

```python
# Test DeviceManager
from device_manager import DeviceManager

dm = DeviceManager()
dm.cache_node_identifiers([{"node_id": "1", "attributes": {"0/40/18": "ABC123"}}])
print(dm.get_device_identifier("1"))  # Returns "ABC123"
```

```python
# Test utils
from utils import normalize_id, safe_json

print(normalize_id("0x0090"))  # Returns "144"
print(safe_json({"key": "value"}))  # Returns JSON string
```

## Code Style

### Naming Conventions
- Classes: PascalCase (`MatterClient`, `AttributeFilter`)
- Functions/Methods: snake_case (`parse_attribute_update`, `get_device_identifier`)
- Constants: UPPER_SNAKE_CASE (used in original, minimal in refactored)
- Private methods: `_snake_case` (`_on_attribute_update`, `_setup_callbacks`)

### Type Hints
All functions have type hints. Examples:
```python
def is_allowed(self, cluster_id: str, attribute_id: str) -> bool:
def parse_attribute_update(message: dict[str, Any]) -> AttributeUpdate | None:
```

### Docstrings
Classes and public methods have docstrings:
```python
def from_file(filter_file: str | None) -> "AttributeFilter":
    """Load attribute filter from JSON file.
    
    Expected JSON format: {...}
    Returns AttributeFilter with no filter if file not provided.
    """
```

## Key Classes

### Config
```python
config = Config(
    url_ws="ws://localhost:5580/ws",
    url_mqtt="mqtt://localhost:1883",
    ...
)
```

### AttributeFilter
```python
filter = AttributeFilter.from_file("filter.json")
if filter.is_allowed("144", "8"):
    name = filter.get_attribute_name("144", "8")
```

### DeviceManager
```python
manager = DeviceManager()
manager.cache_node_identifiers(nodes)
device_id = manager.get_device_identifier(node_id)
is_simple = manager.has_simple_endpoints(node_id)
```

### MatterClient
```python
client = MatterClient("ws://localhost:5580/ws")
await client.consume_messages(
    on_nodes_list=callback1,
    on_attribute_update=callback2,
    stop_event=event
)
```

### MQTTBridge
```python
bridge = MQTTBridge("mqtt://localhost:1883")
bridge.connect()
bridge.publish("topic/name", "payload")
bridge.disconnect()
```

### MatterToMQTTApp
```python
app = MatterToMQTTApp(config)
exit_code = await app.run()
```

## Debugging Tips

### Enable Debug Logging
```bash
python3 main.py --debug debug
```

### Dry Run Mode
```bash
python3 main.py --dry-run
```

### Test with Custom Filter
```bash
python3 main.py --filter custom_filter.json --debug debug
```

### Test WebSocket Connection Only
```bash
python3 main.py --dry-run --debug debug
```

## Performance Considerations

- **Device Caching**: Device identifiers are cached on first update
- **Attribute Filtering**: Checked before building MQTT topic
- **Async Processing**: Uses asyncio for non-blocking I/O
- **Connection Management**: Automatic reconnection with configurable delays
- **MQTT Batching**: Uses paho-mqtt's built-in buffering

## Testing Strategy

### Unit Tests (to add)
```
tests/
├── test_config.py
├── test_utils.py
├── test_attribute_filter.py
├── test_device_manager.py
└── test_mqtt_bridge.py
```

### Integration Tests (to add)
```
tests/
├── test_matter_client.py
├── test_app_integration.py
└── conftest.py  (fixtures)
```

## Troubleshooting

### WebSocket Connection Issues
- Check URL format: `ws://host:port/ws`
- Ensure python-matter-server is running
- Check firewall and network connectivity

### MQTT Connection Issues
- Check URL format: `mqtt://host:port`
- Verify MQTT broker is running
- Try with `--dry-run` to isolate issue

### Filter Not Working
- Verify JSON syntax: `python3 -m json.tool filter.json`
- Check cluster/attribute IDs are in correct format
- Use `--debug debug` to see filtering decisions

### Missing Attributes
- Enable `--debug debug` to see all updates
- Check filter config includes the attribute
- Verify Matter device is properly commissioned

## Resources

- **MATTER_MQTT_README.md** - Original documentation
- **REFACTORED_README.md** - Refactored version docs
- **ARCHITECTURE.md** - Detailed architecture
- **REFACTORING_SUMMARY.md** - Before/after comparison
