"""Configuration management - YAML-based."""

import argparse
import logging
import os
from dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "matter": {
        "url": "ws://127.0.0.1:5580/ws",
        "reconnect_delay": 5.0,
    },
    "mqtt": {
        "url": "mqtt://127.0.0.1:1883",
        "topic_prefix": "matter",
        "username": None,
        "password": None,
    },
    "attributes": {
        "filter": None,
    },
    "logging": {
        "level": "info",
    },
    "advanced": {
        "dry_run": False,
    },
}


@dataclass
class Config:
    """Application configuration."""
    
    url_ws: str
    url_mqtt: str
    mqtt_topic_prefix: str
    mqtt_user: str | None
    mqtt_password: str | None
    filter_file: str | None
    debug_level: str
    dry_run: bool
    reconnect_delay: float

    @staticmethod
    def from_yaml(config_path: str) -> "Config":
        """Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        
        # Merge with defaults
        def deep_merge(base: dict, override: dict) -> dict:
            """Recursively merge override into base."""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged = deep_merge(DEFAULT_CONFIG, config_data)
        
        # Extract values
        matter = merged.get("matter", {})
        mqtt = merged.get("mqtt", {})
        attributes = merged.get("attributes", {})
        logging_cfg = merged.get("logging", {})
        advanced = merged.get("advanced", {})
        
        # Validate required fields
        url_ws = matter.get("url")
        url_mqtt = mqtt.get("url")
        
        if not url_ws:
            raise ValueError("matter.url is required in config")
        if not url_mqtt:
            raise ValueError("mqtt.url is required in config")
        
        return Config(
            url_ws=url_ws,
            url_mqtt=url_mqtt,
            mqtt_topic_prefix=mqtt.get("topic_prefix", "matter"),
            mqtt_user=mqtt.get("username"),
            mqtt_password=mqtt.get("password"),
            filter_file=attributes.get("filter"),
            debug_level=logging_cfg.get("level", "info"),
            dry_run=advanced.get("dry_run", False),
            reconnect_delay=float(matter.get("reconnect_delay", 5.0)),
        )


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Matter WebSocket to MQTT Bridge - Listen to python-matter-server "
            "updates and forward changes to MQTT"
        )
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )
    return parser
