#!/usr/bin/env python3
"""Example: Send Matter device commands via MQTT."""

import json
import sys
import time
import paho.mqtt.client as mqtt


def example_light_control(mqtt_host: str = "localhost", mqtt_port: int = 1883):
    """Example: Control a light via MQTT commands.
    
    Assumes:
    - Matter device with ID: 108ECBDA7AA92CDD (or use your device ID)
    - Endpoint: 1
    - Cluster: 6 (On/Off)
    """
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    def on_connect(client, userdata, connect_flags, reason_code, properties):
        if reason_code == 0:
            print(f"✓ Connected to MQTT broker at {mqtt_host}:{mqtt_port}")
        else:
            print(f"✗ Failed to connect: {reason_code}")
            sys.exit(1)
    
    def on_publish(client, userdata, mid, reason_code, properties):
        if reason_code == 0:
            print("✓ Message published")
        else:
            print(f"✗ Publish failed: {reason_code}")
    
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        print("Connecting to MQTT broker...")
        client.connect(mqtt_host, mqtt_port, keepalive=60)
        client.loop_start()
        time.sleep(0.5)
        
        # Example device (update with your actual device ID)
        device_id = "108ECBDA7AA92CDD"
        endpoint_id = "1"
        cluster_id = "6"  # On/Off
        
        print("\n" + "="*60)
        print("Light Control Examples")
        print("="*60)
        
        # Example 1: Turn ON
        print("\n1. Turning light ON...")
        topic = f"matter/{device_id}/{endpoint_id}/{cluster_id}/command"
        command = {"command": "On", "payload": {}}
        client.publish(topic, json.dumps(command))
        time.sleep(1)
        
        # Example 2: Turn OFF
        print("2. Turning light OFF...")
        command = {"command": "Off", "payload": {}}
        client.publish(topic, json.dumps(command))
        time.sleep(1)
        
        # Example 3: Toggle
        print("3. Toggling light...")
        command = {"command": "Toggle", "payload": {}}
        client.publish(topic, json.dumps(command))
        time.sleep(1)
        
        print("\n" + "="*60)
        print("Brightness Control Example (Cluster 8)")
        print("="*60)
        
        cluster_id = "8"  # Level Control
        topic = f"matter/{device_id}/{endpoint_id}/{cluster_id}/command"
        
        # Example 4: Set brightness to 50%
        print("\n4. Setting brightness to 50%...")
        command = {
            "command": "MoveToLevel",
            "payload": {
                "level": 127,  # 0-254, 127 ≈ 50%
                "transition_time": 0
            }
        }
        client.publish(topic, json.dumps(command))
        time.sleep(1)
        
        # Example 5: Set brightness to 100%
        print("5. Setting brightness to 100%...")
        command = {
            "command": "MoveToLevel",
            "payload": {
                "level": 254,
                "transition_time": 0
            }
        }
        client.publish(topic, json.dumps(command))
        time.sleep(1)
        
        # Example 6: Set brightness to 10%
        print("6. Setting brightness to 10%...")
        command = {
            "command": "MoveToLevel",
            "payload": {
                "level": 25,
                "transition_time": 0
            }
        }
        client.publish(topic, json.dumps(command))
        
        print("\n✓ All examples sent!")
        print("\nCheck the bridge output to see if commands were processed.")
        print("Run: python3 main.py --debug debug")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        time.sleep(1)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    print("Matter MQTT Command Examples")
    print("="*60)
    
    # You can pass custom MQTT host/port
    mqtt_host = "localhost"
    mqtt_port = 1883
    
    if len(sys.argv) > 1:
        mqtt_host = sys.argv[1]
    if len(sys.argv) > 2:
        mqtt_port = int(sys.argv[2])
    
    print(f"MQTT Broker: {mqtt_host}:{mqtt_port}")
    print("\nNote: Update device_id in the script to match your device!")
    print("="*60)
    
    example_light_control(mqtt_host, mqtt_port)
