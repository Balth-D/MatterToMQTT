# Installation & Setup Guide

This guide covers installing the Matter-to-MQTT bridge as a systemd service on a Raspberry Pi or Linux system.

## Prerequisites

- Python 3.10+ installed
- MQTT broker running (Mosquitto or equivalent)
- Matter server running (python-matter-server)
- Raspberry Pi or Linux system with systemd

## Installation Steps

### 1. Clone and Setup Project

```bash
# Clone the repository
cd /opt
sudo git clone <repository-url> MatterToMQTT
cd MatterToMQTT

# Create virtual environment
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# Set proper permissions
sudo chown -R homeassistant:homeassistant /opt/MatterToMQTT
```

### 2. Create Service User (Optional but Recommended)

```bash
# Create a dedicated user for the service
sudo useradd -r -s /bin/false -d /opt/MatterToMQTT homeassistant
```

### 3. Configure the Application and Service

Edit the main configuration file:

```bash
sudo nano /opt/MatterToMQTT/config.yaml
```

Key settings to customize:

| Setting | Description | Example |
|---------|-------------|---------|
| `matter.url` | Matter server WebSocket | `ws://127.0.0.1:5580/ws` |
| `mqtt.url` | MQTT broker URL | `mqtt://127.0.0.1:1883` |
| `mqtt.topic_prefix` | MQTT topic prefix | `matter` |
| `mqtt.username` | MQTT username (optional) | `homeassistant` |
| `mqtt.password` | MQTT password (optional) | **Set securely** |
| `attributes.filter` | Attribute filter file | `examples/attributes_filter_example.json` |
| `logging.level` | Log level | `info` (debug, warning, error) |
| `advanced.dry_run` | Test mode without MQTT | `false` |

### 4. Install Service

```bash
# Copy service file to systemd directory
sudo cp matter-to-mqtt.service /etc/systemd/system/

# Customize the service if needed
sudo nano /etc/systemd/system/matter-to-mqtt.service
# Update: User, WorkingDirectory, MemoryLimit if different

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable matter-to-mqtt

# Start the service
sudo systemctl start matter-to-mqtt
```

### 5. Verify Installation

```bash
# Check service status
sudo systemctl status matter-to-mqtt

# View logs
sudo journalctl -u matter-to-mqtt -f

# View last 50 lines
sudo journalctl -u matter-to-mqtt -n 50
```

## Service Management

### Start/Stop/Restart

```bash
# Start the service
sudo systemctl start matter-to-mqtt

# Stop the service
sudo systemctl stop matter-to-mqtt

# Restart the service
sudo systemctl restart matter-to-mqtt

# Reload configuration (restart if running)
sudo systemctl reload-or-restart matter-to-mqtt

# Disable from auto-start
sudo systemctl disable matter-to-mqtt
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u matter-to-mqtt -f

# Last 100 lines
sudo journalctl -u matter-to-mqtt -n 100

# Since last boot
sudo journalctl -u matter-to-mqtt -b

# Filter by log level
sudo journalctl -u matter-to-mqtt -p err

# Export to file
sudo journalctl -u matter-to-mqtt > matter-to-mqtt.log
```

### Troubleshooting

#### Service won't start

```bash
# Check for syntax errors
sudo systemctl validate matter-to-mqtt

# View detailed error
sudo systemctl start matter-to-mqtt
sudo systemctl status matter-to-mqtt -l

# Check logs
sudo journalctl -u matter-to-mqtt -e
```

#### Configuration file not found

```bash
# Make sure config.yaml exists in WorkingDirectory
ls -la /opt/MatterToMQTT/config.yaml

# Copy default if missing
sudo cp config.yaml /opt/MatterToMQTT/config.yaml
sudo chown homeassistant:homeassistant /opt/MatterToMQTT/config.yaml
sudo chmod 644 /opt/MatterToMQTT/config.yaml
```

#### Permission denied

```bash
# Fix ownership
sudo chown -R homeassistant:homeassistant /opt/MatterToMQTT

# Fix permissions
sudo chmod -R 755 /opt/MatterToMQTT
sudo chmod 644 /opt/MatterToMQTT/config.yaml
```

#### Can't connect to MQTT

```bash
# Test MQTT connection manually
mosquitto_pub -h 127.0.0.1 -u homeassistant -P password -t test -m "hello"

# Check MQTT broker running
sudo systemctl status mosquitto
```

#### Can't connect to Matter server

```bash
# Test Matter server connectivity
curl -v ws://127.0.0.1:5580/ws

# Check Matter server logs
# (depends on your Matter server installation)
```

## Configuration Examples

### Basic Local Setup

```yaml
# config.yaml
matter:
  url: ws://127.0.0.1:5580/ws

mqtt:
  url: mqtt://127.0.0.1:1883
  topic_prefix: matter

logging:
  level: info
```

### With Authentication

```yaml
# config.yaml
matter:
  url: ws://192.168.1.50:5580/ws
  reconnect_delay: 5.0

mqtt:
  url: mqtt://192.168.1.100:1883
  topic_prefix: matter
  username: homeassistant
  password: your_secure_password

attributes:
  filter: examples/attributes_filter_example.json

logging:
  level: info

advanced:
  dry_run: false
```

### Production with Filtering

```yaml
# config.yaml
matter:
  url: ws://192.168.1.50:5580/ws
  reconnect_delay: 10.0

mqtt:
  url: mqtts://192.168.1.100:8883  # Secure MQTT
  topic_prefix: matter
  username: bridge_user
  password: ${MQTT_PASSWORD}  # Set via environment

attributes:
  filter: config/attributes_filter.json

logging:
  level: warning  # Less verbose in production

advanced:
  dry_run: false
```

## Securing Credentials

### Option 1: Direct in Config (Simple, Less Secure)

Edit `config.yaml` with credentials:

```yaml
mqtt:
  username: homeassistant
  password: your_password
```

Protect the file:

```bash
sudo chmod 600 /opt/MatterToMQTT/config.yaml
sudo chown homeassistant:homeassistant /opt/MatterToMQTT/config.yaml
```

### Option 2: Environment Variables (Recommended)

Edit `config.yaml` with placeholders:

```yaml
mqtt:
  username: homeassistant
  password: null  # Will be set via environment
```

Create environment file `/opt/MatterToMQTT/.env`:

```bash
MQTT_PASSWORD=your_secure_password
MQTT_USER=homeassistant
```

Protect the environment file:

```bash
sudo chmod 600 /opt/MatterToMQTT/.env
sudo chown homeassistant:homeassistant /opt/MatterToMQTT/.env
```

## Auto-Restart on Failure

The service is configured to automatically restart if it crashes:

```ini
[Service]
Restart=on-failure
RestartSec=10
```

This means:
- Restarts only on failure (non-zero exit)
- Waits 10 seconds between restart attempts
- Max restart rate: 5 times per 10 seconds (systemd default)

## Resource Limits

Configured limits (adjust as needed):

```ini
[Service]
MemoryLimit=256M        # Max memory usage
MemoryAccounting=true   # Track memory usage
```

Monitor actual usage:

```bash
# Check memory and CPU usage
systemctl status matter-to-mqtt
ps aux | grep matter-to-mqtt
```

## Updating the Service

After updating the code:

```bash
# Pull latest changes
cd /opt/MatterToMQTT
sudo git pull

# Update dependencies if needed
sudo venv/bin/pip install -r requirements.txt

# Restart service
sudo systemctl restart matter-to-mqtt
```

## Removing the Service

```bash
# Stop and disable
sudo systemctl stop matter-to-mqtt
sudo systemctl disable matter-to-mqtt

# Remove service file
sudo rm /etc/systemd/system/matter-to-mqtt.service

# Reload systemd
sudo systemctl daemon-reload
```

## Example Integration with Home Assistant

If running on the same system as Home Assistant:

```yaml
# configuration.yaml
mqtt:
  broker: 127.0.0.1
  port: 1883
  username: homeassistant
  password: !secret mqtt_password

automation:
  - alias: "Light Control via Matter"
    trigger:
      platform: mqtt
      topic: "matter/+/on_off/state"
    action:
      service: notify.telegram_bot
      data:
        message: "Matter light updated: {{ trigger.payload }}"
```

## Next Steps

- See [README.md](../README.md) for command-line usage
- See [BIDIRECTIONAL_GUIDE.md](BIDIRECTIONAL_GUIDE.md) for MQTT topics
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [config.yaml](../config.yaml) for all available options
