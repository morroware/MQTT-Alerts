"""Configuration loader for MQTT Alert Service."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _load_env():
    """Load .env from standard locations."""
    for path in [
        Path("/etc/mqtt-alerts/mqtt-alerts.env"),
        Path.home() / ".config" / "mqtt-alerts" / "mqtt-alerts.env",
        Path("config/mqtt-alerts.env"),
        Path(".env"),
    ]:
        if path.exists():
            load_dotenv(path)
            return
    load_dotenv()


@dataclass
class MQTTConfig:
    host: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "mqtt-alert-service"


@dataclass
class SlackConfig:
    bot_token: str = ""
    default_channel: str = "#alerts"
    rate_limit: int = 10  # max alerts per minute


@dataclass
class Config:
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    db_path: str = "/var/lib/mqtt-alerts/alerts.db"
    log_level: str = "INFO"
    message_retention_days: int = 7
    alert_log_retention_days: int = 30

    @classmethod
    def from_env(cls) -> "Config":
        _load_env()
        return cls(
            mqtt=MQTTConfig(
                host=os.getenv("MQTT_HOST", "localhost"),
                port=int(os.getenv("MQTT_PORT", "1883")),
                username=os.getenv("MQTT_USERNAME", ""),
                password=os.getenv("MQTT_PASSWORD", ""),
                client_id=os.getenv("MQTT_CLIENT_ID", "mqtt-alert-service"),
            ),
            slack=SlackConfig(
                bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
                default_channel=os.getenv("SLACK_DEFAULT_CHANNEL", "#alerts"),
                rate_limit=int(os.getenv("SLACK_RATE_LIMIT", "10")),
            ),
            db_path=os.getenv("DB_PATH", "/var/lib/mqtt-alerts/alerts.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            message_retention_days=int(os.getenv("MESSAGE_RETENTION_DAYS", "7")),
            alert_log_retention_days=int(os.getenv("ALERT_LOG_RETENTION_DAYS", "30")),
        )
