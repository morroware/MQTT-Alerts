"""MQTT subscriber that connects to broker and dispatches messages."""

import asyncio
import functools
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from sqlalchemy import select

from .config import MQTTConfig
from .database import get_session_factory
from .models import AlertLog, Message, Rule, Topic
from .rule_engine import RuleEngine
from .slack_notifier import SlackNotifier

logger = logging.getLogger(__name__)


class MQTTClient:
    """Connects to MQTT broker, subscribes to topics, evaluates rules, sends alerts."""

    def __init__(self, mqtt_config: MQTTConfig, notifier: SlackNotifier):
        self._config = mqtt_config
        self._notifier = notifier
        self._rule_engine = RuleEngine()
        self._client: mqtt.Client | None = None
        self._rules: list[dict] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False
        self._subscribed_topics: set[str] = set()

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self, loop: asyncio.AbstractEventLoop):
        """Start the MQTT client on the given event loop."""
        self._loop = loop

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._config.client_id,
            clean_session=self._config.clean_session,
        )

        if self._config.username:
            self._client.username_pw_set(self._config.username, self._config.password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self._client.connect_async(
                self._config.host, self._config.port, keepalive=self._config.keepalive
            )
            self._client.loop_start()
            logger.info(
                "MQTT client connecting to %s:%d", self._config.host, self._config.port
            )
        except Exception as e:
            logger.error("Failed to start MQTT client: %s", e)

    def stop(self):
        """Stop the MQTT client."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("MQTT client stopped")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker")
            # Re-subscribe to all topics with configured QoS
            for topic in self._subscribed_topics:
                client.subscribe(topic, qos=self._config.qos)
                logger.info("Subscribed to: %s (QoS %d)", topic, self._config.qos)
        else:
            self._connected = False
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self._connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect (rc=%d), will reconnect", rc)

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message — runs in paho's network thread."""
        topic = msg.topic
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            payload = str(msg.payload)

        # Strip null bytes — common in PLC payloads (AutomationDirect, etc.)
        payload = payload.replace("\x00", "").strip()

        logger.debug("Message on %s: %s", topic, payload[:200])

        # Schedule async processing on the main event loop
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._process_message(topic, payload, msg.qos, msg.retain),
                self._loop,
            )

    async def _process_message(
        self, topic: str, payload: str, qos: int, retained: bool
    ):
        """Store message and evaluate rules (runs on asyncio loop)."""
        try:
            session_factory = get_session_factory()

            # Store message
            async with session_factory() as session:
                message = Message(
                    topic=topic,
                    payload=payload,
                    qos=qos,
                    retained=retained,
                    received_at=datetime.now(timezone.utc),
                )
                session.add(message)
                await session.commit()
                message_id = message.id

            # Evaluate rules
            matches = self._rule_engine.evaluate(topic, payload, self._rules)

            for match in matches:
                if match.matched:
                    # Run synchronous Slack API call in executor to avoid
                    # blocking the asyncio event loop
                    loop = asyncio.get_running_loop()
                    success, response = await loop.run_in_executor(
                        None,
                        functools.partial(
                            self._notifier.send_alert,
                            topic=topic,
                            payload=payload,
                            rule_name=match.rule_name,
                            severity=match.severity,
                            details=match.details,
                            channel=match.slack_channel,
                            message_template=match.message_template,
                        ),
                    )

                    # Log the alert
                    async with session_factory() as session:
                        alert = AlertLog(
                            rule_id=match.rule_id,
                            message_id=message_id,
                            rule_name=match.rule_name,
                            topic=topic,
                            severity=match.severity,
                            slack_response=response,
                            sent_at=datetime.now(timezone.utc),
                        )
                        session.add(alert)

                        # Update last_triggered on the rule
                        result = await session.execute(
                            select(Rule).where(Rule.id == match.rule_id)
                        )
                        rule = result.scalar_one_or_none()
                        if rule:
                            rule.last_triggered = datetime.now(timezone.utc)

                        await session.commit()
        except Exception as e:
            logger.error("Error processing message on %s: %s", topic, e)

    async def refresh_subscriptions(self):
        """Reload topics and rules from database."""
        session_factory = get_session_factory()

        async with session_factory() as session:
            # Load enabled topics
            result = await session.execute(
                select(Topic).where(Topic.enabled == True)  # noqa: E712
            )
            topics = result.scalars().all()
            new_topics = {t.topic_pattern for t in topics}

            # Load enabled rules
            result = await session.execute(
                select(Rule).where(Rule.enabled == True)  # noqa: E712
            )
            rules = result.scalars().all()
            self._rules = [
                {
                    "id": r.id,
                    "name": r.name,
                    "topic_pattern": r.topic_pattern,
                    "condition_type": r.condition_type,
                    "condition_value": r.condition_value,
                    "condition_operator": r.condition_operator,
                    "severity": r.severity,
                    "slack_channel": r.slack_channel,
                    "message_template": r.message_template,
                    "cooldown_seconds": r.cooldown_seconds,
                    "enabled": r.enabled,
                }
                for r in rules
            ]

        # Update subscriptions
        if self._client and self._connected:
            # Unsubscribe from removed topics
            removed = self._subscribed_topics - new_topics
            for topic in removed:
                self._client.unsubscribe(topic)
                logger.info("Unsubscribed from: %s", topic)

            # Subscribe to new topics with configured QoS
            added = new_topics - self._subscribed_topics
            for topic in added:
                self._client.subscribe(topic, qos=self._config.qos)
                logger.info("Subscribed to: %s (QoS %d)", topic, self._config.qos)

            self._subscribed_topics = new_topics

        logger.info(
            "Refreshed: %d topics, %d rules", len(new_topics), len(self._rules)
        )
