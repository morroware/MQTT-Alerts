"""Tests for the Slack notifier (without real API calls)."""

from mqtt_alerts.slack_notifier import SlackNotifier


class TestSlackNotifier:
    def test_no_token(self):
        notifier = SlackNotifier(bot_token="", default_channel="#test", rate_limit=10)
        ok, msg = notifier.validate()
        assert not ok
        assert "No bot token" in msg

    def test_send_without_token(self):
        notifier = SlackNotifier(bot_token="", default_channel="#test", rate_limit=10)
        ok, msg = notifier.send_alert(
            topic="test/topic",
            payload="hello",
            rule_name="Test Rule",
            severity="info",
            details="test",
        )
        assert not ok

    def test_rate_limit(self):
        notifier = SlackNotifier(bot_token="", default_channel="#test", rate_limit=2)
        # Manually fill the send times to simulate rate limit
        import time
        notifier._send_times.extend([time.time(), time.time()])
        assert not notifier._check_rate_limit()

    def test_rate_limit_allows_after_window(self):
        notifier = SlackNotifier(bot_token="", default_channel="#test", rate_limit=2)
        import time
        # Add timestamps from 2 minutes ago (outside the 60s window)
        old = time.time() - 120
        notifier._send_times.extend([old, old])
        assert notifier._check_rate_limit()

    def test_update_token(self):
        notifier = SlackNotifier(bot_token="", default_channel="#test", rate_limit=10)
        assert notifier._client is None
        notifier.update_token("xoxb-fake-token")
        assert notifier._client is not None

    def test_send_no_channel(self):
        notifier = SlackNotifier(bot_token="xoxb-fake", default_channel="", rate_limit=10)
        ok, msg = notifier.send_alert(
            topic="test/topic",
            payload="hello",
            rule_name="Test Rule",
            severity="info",
            details="test",
            channel="",
        )
        assert not ok
        assert "No channel" in msg
