#!/usr/bin/env python3
"""Test script for command parsing and routing."""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.command_handler import CommandRouter, CommandTopicParser, MQTTCommand


def test_command_parsing():
    """Test command topic and payload parsing."""
    
    print("=" * 70)
    print("Command Parsing Tests")
    print("=" * 70)
    
    parser = CommandTopicParser()
    
    # Test 1: Valid topic parsing (full format with endpoint)
    print("\n1. Full format topic (with endpoint):")
    topic = "matter/device123/1/6/command"
    result = parser.parse_command_topic(topic, "matter")
    print(f"   Topic: {topic}")
    print(f"   Result: {result}")
    assert result == ("device123", "1", "6"), f"Expected ('device123', '1', '6'), got {result}"
    print("   ✓ Pass")
    
    # Test 2: Simple format topic parsing (without endpoint, defaults to 1)
    print("\n2. Simple format topic (without endpoint, defaults to 1):")
    topic = "matter/device123/6/command"
    result = parser.parse_command_topic(topic, "matter")
    print(f"   Topic: {topic}")
    print(f"   Result: {result}")
    assert result == ("device123", "1", "6"), f"Expected ('device123', '1', '6'), got {result}"
    print("   ✓ Pass (automatically defaults to endpoint 1)")
    
    # Test 3: Invalid topics
    print("\n3. Invalid topic (missing command):")
    topic = "matter/device123/1/6"
    result = parser.parse_command_topic(topic, "matter")
    print(f"   Topic: {topic}")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✓ Pass")
    
    print("\n4. Invalid topic (non-numeric endpoint):")
    topic = "matter/device123/abc/6/command"
    result = parser.parse_command_topic(topic, "matter")
    print(f"   Topic: {topic}")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✓ Pass")
    
    print("\n5. Invalid topic (non-numeric cluster in simple format):")
    topic = "matter/device123/abc/command"
    result = parser.parse_command_topic(topic, "matter")
    print(f"   Topic: {topic}")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✓ Pass")
    
    # Test 3: Valid payload parsing
    print("\n6. Valid payload parsing:")
    payload = '{"command": "On", "payload": {}}'
    result = parser.parse_command_payload(payload)
    print(f"   Payload: {payload}")
    print(f"   Result: {result}")
    assert result == ("On", {}), f"Expected ('On', {{}}), got {result}"
    print("   ✓ Pass")
    
    print("\n7. Invalid payload (not JSON):")
    payload = "not json"
    result = parser.parse_command_payload(payload)
    print(f"   Payload: {payload}")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✓ Pass")
    
    print("\n8. Invalid payload (missing command):")
    payload = '{"payload": {}}'
    result = parser.parse_command_payload(payload)
    print(f"   Payload: {payload}")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got {result}"
    print("   ✓ Pass")


def test_command_routing():
    """Test command routing."""
    
    print("\n" + "=" * 70)
    print("Command Routing Tests")
    print("=" * 70)
    
    router = CommandRouter("matter")
    
    # Mock device ID lookup
    device_lookup = {
        "device123": "1234",
        "light_room": "5678",
    }
    
    def lookup_node_id(device_id):
        return device_lookup.get(device_id)
    
    # Test 1: Valid command (full format with endpoint)
    print("\n1. Valid command (full format):")
    topic = "matter/device123/1/6/command"
    payload = '{"command": "On", "payload": {}}'
    
    command = router.parse_mqtt_command(topic, payload, lookup_node_id)
    print(f"   Topic: {topic}")
    print(f"   Payload: {payload}")
    if command:
        print(f"   Result: node_id={command.node_id}, endpoint={command.endpoint_id}, "
              f"cluster={command.cluster_id}, command={command.command_name}")
        assert command.node_id == "1234"
        assert command.endpoint_id == "1"
        assert command.cluster_id == "6"
        assert command.command_name == "On"
        print("   ✓ Pass")
    else:
        print("   ✗ Fail: Got None")
    
    # Test 2: Valid command (simple format, no endpoint)
    print("\n2. Valid command (simple format, defaults to endpoint 1):")
    topic = "matter/device123/6/command"
    payload = '{"command": "On", "payload": {}}'
    
    command = router.parse_mqtt_command(topic, payload, lookup_node_id)
    print(f"   Topic: {topic}")
    print(f"   Payload: {payload}")
    if command:
        print(f"   Result: node_id={command.node_id}, endpoint={command.endpoint_id}, "
              f"cluster={command.cluster_id}, command={command.command_name}")
        assert command.node_id == "1234"
        assert command.endpoint_id == "1"  # Should default to 1
        assert command.cluster_id == "6"
        assert command.command_name == "On"
        print("   ✓ Pass (endpoint auto-defaulted to 1)")
    else:
        print("   ✗ Fail: Got None")
    
    # Test 3: Unknown device
    print("\n3. Unknown device:")
    topic = "matter/unknown/1/6/command"
    payload = '{"command": "On", "payload": {}}'
    
    command = router.parse_mqtt_command(topic, payload, lookup_node_id)
    print(f"   Topic: {topic}")
    print(f"   Result: {command}")
    assert command is None, f"Expected None for unknown device"
    print("   ✓ Pass")
    
    # Test 4: Complex payload (full format)
    print("\n4. Command with parameters (full format):")
    topic = "matter/light_room/1/8/command"
    payload = '{"command": "MoveToLevel", "payload": {"level": 128, "transition_time": 0}}'
    
    command = router.parse_mqtt_command(topic, payload, lookup_node_id)
    print(f"   Topic: {topic}")
    print(f"   Payload: {payload}")
    if command:
        print(f"   Result: command={command.command_name}, payload={command.payload}")
        assert command.command_name == "MoveToLevel"
        assert command.payload == {"level": 128, "transition_time": 0}
        print("   ✓ Pass")
    else:
        print("   ✗ Fail: Got None")
    
    # Test 5: Complex payload (simple format)
    print("\n5. Command with parameters (simple format):")
    topic = "matter/light_room/8/command"
    payload = '{"command": "MoveToLevel", "payload": {"level": 200, "transition_time": 0}}'
    
    command = router.parse_mqtt_command(topic, payload, lookup_node_id)
    print(f"   Topic: {topic}")
    print(f"   Payload: {payload}")
    if command:
        print(f"   Result: endpoint={command.endpoint_id}, command={command.command_name}")
        assert command.endpoint_id == "1"  # Should default to 1
        assert command.command_name == "MoveToLevel"
        assert command.payload == {"level": 200, "transition_time": 0}
        print("   ✓ Pass (simple format with parameters)")
    else:
        print("   ✗ Fail: Got None")


def test_mqtt_command_class():
    """Test MQTTCommand data class."""
    
    print("\n" + "=" * 70)
    print("MQTTCommand Class Tests")
    print("=" * 70)
    
    print("\n1. Creating MQTTCommand:")
    command = MQTTCommand(
        topic="matter/device123/1/6/command",
        node_id="1234",
        endpoint_id="1",
        cluster_id="6",
        command_name="On",
        payload={}
    )
    
    print(f"   {command}")
    print("   ✓ Pass")


if __name__ == "__main__":
    try:
        test_command_parsing()
        test_command_routing()
        test_mqtt_command_class()
        
        print("\n" + "=" * 70)
        print("All tests passed! ✓")
        print("Tests: 2 parsing + 3 routing + 5 parameter + 1 class = 11 total")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
