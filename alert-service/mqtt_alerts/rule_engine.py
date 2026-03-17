"""Rule engine for evaluating MQTT messages against alert rules."""

import json
import logging
import re
import signal
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RuleMatch:
    """Result of a rule evaluation."""
    rule_id: int
    rule_name: str
    severity: str
    slack_channel: str
    message_template: str
    matched: bool
    details: str = ""


def _mqtt_topic_matches(pattern: str, topic: str) -> bool:
    """Check if an MQTT topic matches a pattern (supports + and # wildcards)."""
    pattern_parts = pattern.split("/")
    topic_parts = topic.split("/")

    i = 0
    for i, pat in enumerate(pattern_parts):
        if pat == "#":
            return True
        if i >= len(topic_parts):
            return False
        if pat != "+" and pat != topic_parts[i]:
            return False

    return len(pattern_parts) == len(topic_parts)


def _extract_json_field(payload: str, field_path: str):
    """Extract a value from a JSON payload using dot notation (e.g. 'data.temp')."""
    try:
        obj = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None

    parts = field_path.split(".")
    for part in parts:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        elif isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return obj


def _compare(value, operator: str, target_str: str) -> bool:
    """Compare a value against a target using the specified operator."""
    try:
        # Try numeric comparison first
        num_value = float(value)
        num_target = float(target_str)
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }
        return ops.get(operator, lambda a, b: False)(num_value, num_target)
    except (ValueError, TypeError):
        # Fall back to string comparison
        str_value = str(value)
        if operator == "==":
            return str_value == target_str
        if operator == "!=":
            return str_value != target_str
        return False


@dataclass
class RuleEngine:
    """Evaluates messages against alert rules with cooldown tracking."""

    # rule_id -> last trigger timestamp
    _cooldowns: dict[int, float] = field(default_factory=dict)

    def evaluate(self, topic: str, payload: str, rules: list[dict]) -> list[RuleMatch]:
        """Evaluate a message against all enabled rules. Returns list of matches."""
        matches = []

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            # Check topic match
            if not _mqtt_topic_matches(rule["topic_pattern"], topic):
                continue

            # Check cooldown
            rule_id = rule["id"]
            cooldown = rule.get("cooldown_seconds", 60)
            last_triggered = self._cooldowns.get(rule_id, 0)
            if time.time() - last_triggered < cooldown:
                continue

            # Evaluate condition
            matched, details = self._evaluate_condition(
                payload,
                rule.get("condition_type", "any"),
                rule.get("condition_value", ""),
                rule.get("condition_operator", "=="),
            )

            if matched:
                self._cooldowns[rule_id] = time.time()
                matches.append(
                    RuleMatch(
                        rule_id=rule_id,
                        rule_name=rule.get("name", ""),
                        severity=rule.get("severity", "info"),
                        slack_channel=rule.get("slack_channel", ""),
                        message_template=rule.get("message_template", ""),
                        matched=True,
                        details=details,
                    )
                )

        return matches

    def _evaluate_condition(
        self, payload: str, condition_type: str, condition_value: str, operator: str
    ) -> tuple[bool, str]:
        """Evaluate a single condition. Returns (matched, details)."""

        if condition_type == "any":
            return True, "Matched: any message"

        if condition_type == "contains":
            if condition_value in payload:
                return True, f"Payload contains '{condition_value}'"
            return False, ""

        if condition_type == "regex":
            try:
                # Compile with a length check to mitigate overly complex patterns
                if len(condition_value) > 1000:
                    logger.warning("Regex pattern too long (%d chars), skipping", len(condition_value))
                    return False, ""
                match = re.search(condition_value, payload, re.DOTALL)
                if match:
                    return True, f"Payload matches regex '{condition_value}'"
            except re.error as e:
                logger.warning("Invalid regex '%s': %s", condition_value, e)
            return False, ""

        if condition_type == "json_path":
            # condition_value format: "field.path|compare_value"
            # e.g. "temperature|30" with operator ">"
            parts = condition_value.split("|", 1)
            if len(parts) != 2:
                logger.warning("Invalid json_path condition: %s", condition_value)
                return False, ""
            field_path, target = parts
            extracted = _extract_json_field(payload, field_path)
            if extracted is not None and _compare(extracted, operator, target):
                return True, f"{field_path}={extracted} {operator} {target}"
            return False, ""

        if condition_type == "threshold":
            try:
                value = float(payload.strip())
                target = float(condition_value)
                if _compare(value, operator, condition_value):
                    return True, f"Value {value} {operator} {target}"
            except (ValueError, TypeError):
                pass
            return False, ""

        logger.warning("Unknown condition type: %s", condition_type)
        return False, ""

    def test_rule(self, topic: str, payload: str, rule: dict) -> RuleMatch:
        """Test a single rule against a sample message (ignores cooldown)."""
        if not _mqtt_topic_matches(rule.get("topic_pattern", ""), topic):
            return RuleMatch(
                rule_id=rule.get("id", 0),
                rule_name=rule.get("name", ""),
                severity=rule.get("severity", "info"),
                slack_channel=rule.get("slack_channel", ""),
                message_template=rule.get("message_template", ""),
                matched=False,
                details="Topic pattern did not match",
            )

        matched, details = self._evaluate_condition(
            payload,
            rule.get("condition_type", "any"),
            rule.get("condition_value", ""),
            rule.get("condition_operator", "=="),
        )

        return RuleMatch(
            rule_id=rule.get("id", 0),
            rule_name=rule.get("name", ""),
            severity=rule.get("severity", "info"),
            slack_channel=rule.get("slack_channel", ""),
            message_template=rule.get("message_template", ""),
            matched=matched,
            details=details if matched else "Condition not met",
        )
