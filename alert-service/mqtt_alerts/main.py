"""MQTT Alert Service — main entry point."""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete

from .config import Config
from .database import close_db, init_db, get_session_factory
from .models import AlertLog, Message
from .mqtt_client import MQTTClient
from .slack_notifier import SlackNotifier

logger = logging.getLogger("mqtt_alerts")

HEALTH_FILE = Path("/tmp/mqtt-alert-service.health")


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def retention_cleanup(config: Config):
    """Delete old messages and alert logs based on retention settings."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Clean old messages
        cutoff = datetime.now(timezone.utc) - timedelta(days=config.message_retention_days)
        result = await session.execute(
            delete(Message).where(Message.received_at < cutoff)
        )
        msg_count = result.rowcount

        # Clean old alert logs
        cutoff = datetime.now(timezone.utc) - timedelta(days=config.alert_log_retention_days)
        result = await session.execute(
            delete(AlertLog).where(AlertLog.sent_at < cutoff)
        )
        alert_count = result.rowcount

        await session.commit()

    if msg_count or alert_count:
        logger.info("Retention cleanup: removed %d messages, %d alert logs", msg_count, alert_count)


async def run_service():
    """Main service loop."""
    config = Config.from_env()
    setup_logging(config.log_level)
    logger.info("MQTT Alert Service starting...")

    # Initialize database
    await init_db(config.db_path)

    # Initialize Slack notifier
    notifier = SlackNotifier(
        bot_token=config.slack.bot_token,
        default_channel=config.slack.default_channel,
        rate_limit=config.slack.rate_limit,
    )

    # Check Slack token if configured
    if config.slack.bot_token:
        ok, identity = notifier.validate()
        if ok:
            logger.info("Slack bot ready: %s", identity)
        else:
            logger.warning("Slack bot token invalid: %s (alerts will fail)", identity)
    else:
        logger.warning("No Slack bot token configured — alerts will be logged only")

    # Initialize MQTT client
    loop = asyncio.get_running_loop()
    mqtt_client = MQTTClient(config.mqtt, notifier)
    mqtt_client.start(loop)

    # Initial subscription load
    await mqtt_client.refresh_subscriptions()

    # Setup shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down...", sig)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # Write health file
    HEALTH_FILE.write_text(json.dumps({
        "status": "running",
        "pid": str(asyncio.get_running_loop()._thread_id if hasattr(asyncio.get_running_loop(), '_thread_id') else "unknown"),
        "started": datetime.now(timezone.utc).isoformat(),
    }))

    logger.info("Service ready — monitoring MQTT topics")

    # Main loop: refresh subscriptions and run cleanup periodically
    refresh_interval = 30  # seconds
    cleanup_interval = 3600  # 1 hour
    last_cleanup = asyncio.get_event_loop().time()

    try:
        while not shutdown_event.is_set():
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=refresh_interval)
                break  # shutdown requested
            except asyncio.TimeoutError:
                pass  # normal timeout — do periodic work

            # Refresh subscriptions from DB
            try:
                await mqtt_client.refresh_subscriptions()
            except Exception as e:
                logger.error("Failed to refresh subscriptions: %s", e)

            # Periodic retention cleanup
            now = asyncio.get_event_loop().time()
            if now - last_cleanup >= cleanup_interval:
                try:
                    await retention_cleanup(config)
                except Exception as e:
                    logger.error("Retention cleanup failed: %s", e)
                last_cleanup = now

            # Update health file
            HEALTH_FILE.write_text(json.dumps({
                "status": "running",
                "mqtt_connected": mqtt_client.connected,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
    finally:
        logger.info("Shutting down...")
        mqtt_client.stop()
        await close_db()
        if HEALTH_FILE.exists():
            HEALTH_FILE.unlink()
        logger.info("Service stopped")


def main():
    try:
        asyncio.run(run_service())
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
