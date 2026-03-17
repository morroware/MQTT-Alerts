"""Slack Bot API notification dispatcher."""

import logging
import time
from collections import deque
from datetime import datetime, timezone

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "info": "#2196F3",
    "warning": "#FF9800",
    "critical": "#F44336",
}

SEVERITY_EMOJI = {
    "info": ":information_source:",
    "warning": ":warning:",
    "critical": ":rotating_light:",
}


class SlackNotifier:
    """Sends alert messages to Slack using a Bot Token."""

    def __init__(self, bot_token: str, default_channel: str, rate_limit: int = 10):
        self.default_channel = default_channel
        self.rate_limit = rate_limit
        self._client = WebClient(token=bot_token) if bot_token else None
        self._send_times: deque[float] = deque()
        self._bot_name: str = ""

    def validate(self) -> tuple[bool, str]:
        """Validate the bot token and return (ok, identity_or_error)."""
        if not self._client:
            return False, "No bot token configured"
        try:
            resp = self._client.auth_test()
            self._bot_name = resp.get("bot_id", "unknown")
            user = resp.get("user", "unknown")
            team = resp.get("team", "unknown")
            logger.info("Slack bot authenticated: %s @ %s", user, team)
            return True, f"{user} @ {team}"
        except SlackApiError as e:
            msg = e.response.get("error", str(e)) if e.response else str(e)
            logger.error("Slack auth failed: %s", msg)
            return False, msg

    def update_token(self, bot_token: str):
        """Update the bot token at runtime."""
        self._client = WebClient(token=bot_token) if bot_token else None

    def _check_rate_limit(self) -> bool:
        """Return True if we can send (under rate limit)."""
        now = time.time()
        # Remove timestamps older than 60 seconds
        while self._send_times and self._send_times[0] < now - 60:
            self._send_times.popleft()
        return len(self._send_times) < self.rate_limit

    def send_alert(
        self,
        topic: str,
        payload: str,
        rule_name: str,
        severity: str,
        details: str,
        channel: str = "",
        message_template: str = "",
    ) -> tuple[bool, str]:
        """Send an alert to Slack. Returns (success, response_or_error)."""
        if not self._client:
            return False, "No bot token configured"

        if not self._check_rate_limit():
            logger.warning("Rate limit exceeded, skipping alert for rule '%s'", rule_name)
            return False, "Rate limit exceeded"

        target_channel = channel or self.default_channel
        if not target_channel:
            return False, "No channel configured"

        color = SEVERITY_COLORS.get(severity, "#757575")
        emoji = SEVERITY_EMOJI.get(severity, ":bell:")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Use custom template or default
        if message_template:
            try:
                text = message_template.format(
                    topic=topic,
                    payload=payload,
                    rule=rule_name,
                    severity=severity,
                    details=details,
                    timestamp=now,
                )
            except (KeyError, IndexError, ValueError) as e:
                logger.warning("Bad message template for rule '%s': %s", rule_name, e)
                text = f"{emoji} *MQTT Alert* — {severity.upper()}"
        else:
            text = f"{emoji} *MQTT Alert* — {severity.upper()}"

        # Truncate payload for display
        payload_display = payload[:500] + "..." if len(payload) > 500 else payload

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} MQTT Alert — {severity.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Rule:*\n{rule_name}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                    {"type": "mrkdwn", "text": f"*Topic:*\n`{topic}`"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{now}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Payload:*\n```{payload_display}```",
                },
            },
        ]

        if details:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"*Match details:* {details}"}
                    ],
                }
            )

        try:
            resp = self._client.chat_postMessage(
                channel=target_channel,
                text=text,
                blocks=blocks,
                unfurl_links=False,
            )
            self._send_times.append(time.time())
            logger.info(
                "Alert sent to %s for rule '%s' (ts: %s)",
                target_channel, rule_name, resp.get("ts", ""),
            )
            return True, f"ok (ts: {resp.get('ts', '')})"
        except SlackApiError as e:
            msg = e.response.get("error", str(e)) if e.response else str(e)
            logger.error("Failed to send alert: %s", msg)
            return False, msg

    def send_test_message(self, channel: str) -> tuple[bool, str]:
        """Send a test message to verify configuration."""
        if not self._client:
            return False, "No bot token configured"

        try:
            resp = self._client.chat_postMessage(
                channel=channel,
                text=":white_check_mark: MQTT-Alerts test message — Slack integration is working!",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":white_check_mark: *MQTT-Alerts Test*\nSlack integration is working correctly!",
                        },
                    }
                ],
            )
            return True, f"ok (ts: {resp.get('ts', '')})"
        except SlackApiError as e:
            msg = e.response.get("error", str(e)) if e.response else str(e)
            return False, msg

    def list_channels(self) -> tuple[bool, list[dict]]:
        """List channels the bot can post to."""
        if not self._client:
            return False, []

        try:
            channels = []
            cursor = None
            while True:
                resp = self._client.conversations_list(
                    types="public_channel,private_channel",
                    limit=200,
                    cursor=cursor,
                )
                for ch in resp.get("channels", []):
                    channels.append({
                        "id": ch["id"],
                        "name": ch["name"],
                        "is_private": ch.get("is_private", False),
                        "is_member": ch.get("is_member", False),
                    })
                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
            return True, channels
        except SlackApiError as e:
            msg = e.response.get("error", str(e)) if e.response else str(e)
            logger.error("Failed to list channels: %s", msg)
            return False, []
