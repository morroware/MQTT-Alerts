"""Tests for the rule engine."""

import json
import time

from mqtt_alerts.rule_engine import RuleEngine, _mqtt_topic_matches


def _make_rule(**overrides):
    defaults = {
        "id": 1,
        "name": "Test Rule",
        "topic_pattern": "test/#",
        "condition_type": "any",
        "condition_value": "",
        "condition_operator": "==",
        "severity": "info",
        "slack_channel": "",
        "message_template": "",
        "cooldown_seconds": 0,
        "enabled": True,
    }
    defaults.update(overrides)
    return defaults


class TestTopicMatching:
    def test_exact_match(self):
        assert _mqtt_topic_matches("home/temp", "home/temp")

    def test_no_match(self):
        assert not _mqtt_topic_matches("home/temp", "home/humidity")

    def test_plus_wildcard(self):
        assert _mqtt_topic_matches("home/+/temp", "home/living/temp")
        assert not _mqtt_topic_matches("home/+/temp", "home/living/humidity")

    def test_hash_wildcard(self):
        assert _mqtt_topic_matches("home/#", "home/living/temp")
        assert _mqtt_topic_matches("home/#", "home")

    def test_multi_level(self):
        assert _mqtt_topic_matches("sensors/+/data", "sensors/node1/data")
        assert not _mqtt_topic_matches("sensors/+/data", "sensors/node1/config")


class TestRuleEngine:
    def test_any_condition(self):
        engine = RuleEngine()
        rule = _make_rule(condition_type="any")
        matches = engine.evaluate("test/topic", "hello", [rule])
        assert len(matches) == 1
        assert matches[0].matched

    def test_contains_condition(self):
        engine = RuleEngine()
        rule = _make_rule(condition_type="contains", condition_value="error")
        matches = engine.evaluate("test/topic", "an error occurred", [rule])
        assert len(matches) == 1
        assert "error" in matches[0].details

    def test_contains_no_match(self):
        engine = RuleEngine()
        rule = _make_rule(condition_type="contains", condition_value="error")
        matches = engine.evaluate("test/topic", "all good", [rule])
        assert len(matches) == 0

    def test_regex_condition(self):
        engine = RuleEngine()
        rule = _make_rule(condition_type="regex", condition_value=r"temp:\s*\d+")
        matches = engine.evaluate("test/topic", "temp: 42", [rule])
        assert len(matches) == 1

    def test_regex_no_match(self):
        engine = RuleEngine()
        rule = _make_rule(condition_type="regex", condition_value=r"temp:\s*\d+")
        matches = engine.evaluate("test/topic", "humidity: high", [rule])
        assert len(matches) == 0

    def test_json_path_condition(self):
        engine = RuleEngine()
        rule = _make_rule(
            condition_type="json_path",
            condition_value="temperature|30",
            condition_operator=">",
        )
        payload = json.dumps({"temperature": 35})
        matches = engine.evaluate("test/topic", payload, [rule])
        assert len(matches) == 1
        assert "35" in matches[0].details

    def test_json_path_nested(self):
        engine = RuleEngine()
        rule = _make_rule(
            condition_type="json_path",
            condition_value="data.value|100",
            condition_operator=">=",
        )
        payload = json.dumps({"data": {"value": 150}})
        matches = engine.evaluate("test/topic", payload, [rule])
        assert len(matches) == 1

    def test_threshold_condition(self):
        engine = RuleEngine()
        rule = _make_rule(
            condition_type="threshold",
            condition_value="50",
            condition_operator=">",
        )
        matches = engine.evaluate("test/topic", "75", [rule])
        assert len(matches) == 1

    def test_cooldown(self):
        engine = RuleEngine()
        rule = _make_rule(cooldown_seconds=60)
        matches1 = engine.evaluate("test/topic", "msg1", [rule])
        assert len(matches1) == 1
        matches2 = engine.evaluate("test/topic", "msg2", [rule])
        assert len(matches2) == 0  # cooldown active

    def test_disabled_rule(self):
        engine = RuleEngine()
        rule = _make_rule(enabled=False)
        matches = engine.evaluate("test/topic", "hello", [rule])
        assert len(matches) == 0

    def test_topic_mismatch(self):
        engine = RuleEngine()
        rule = _make_rule(topic_pattern="other/#")
        matches = engine.evaluate("test/topic", "hello", [rule])
        assert len(matches) == 0

    def test_multiple_rules(self):
        engine = RuleEngine()
        rules = [
            _make_rule(id=1, name="Rule 1", condition_type="any", cooldown_seconds=0),
            _make_rule(
                id=2,
                name="Rule 2",
                condition_type="contains",
                condition_value="alert",
                cooldown_seconds=0,
            ),
        ]
        matches = engine.evaluate("test/topic", "alert fired", rules)
        assert len(matches) == 2

    def test_test_rule_ignores_cooldown(self):
        engine = RuleEngine()
        rule = _make_rule(cooldown_seconds=9999)
        # Trigger once to set cooldown
        engine.evaluate("test/topic", "msg", [rule])
        # test_rule should still work
        result = engine.test_rule("test/topic", "msg", rule)
        assert result.matched
