"""Alert rule management API routes."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Rule, get_session_factory

# Import rule engine for testing
_alert_service_path = str(Path(__file__).parent.parent.parent.parent / "alert-service")
if _alert_service_path not in sys.path:
    sys.path.insert(0, _alert_service_path)
from mqtt_alerts.rule_engine import RuleEngine  # noqa: E402

router = APIRouter(prefix="/api/rules", tags=["rules"])
_test_engine = RuleEngine()


class RuleCreate(BaseModel):
    name: str
    topic_pattern: str
    condition_type: str = "any"
    condition_value: str = ""
    condition_operator: str = "=="
    severity: str = "info"
    slack_channel: str = ""
    message_template: str = ""
    cooldown_seconds: int = 60
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: str | None = None
    topic_pattern: str | None = None
    condition_type: str | None = None
    condition_value: str | None = None
    condition_operator: str | None = None
    severity: str | None = None
    slack_channel: str | None = None
    message_template: str | None = None
    cooldown_seconds: int | None = None
    enabled: bool | None = None


class RuleTest(BaseModel):
    topic: str
    payload: str


async def get_db():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


def _rule_to_dict(r: Rule) -> dict:
    return {
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
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
    }


@router.get("")
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).order_by(Rule.created_at.desc()))
    return [_rule_to_dict(r) for r in result.scalars().all()]


@router.post("", status_code=201)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db)):
    # Validate condition type
    valid_types = {"any", "contains", "regex", "json_path", "threshold"}
    if body.condition_type not in valid_types:
        raise HTTPException(400, f"Invalid condition_type. Must be one of: {valid_types}")

    valid_operators = {"==", "!=", ">", "<", ">=", "<="}
    if body.condition_operator not in valid_operators:
        raise HTTPException(400, f"Invalid condition_operator. Must be one of: {valid_operators}")

    valid_severities = {"info", "warning", "critical"}
    if body.severity not in valid_severities:
        raise HTTPException(400, f"Invalid severity. Must be one of: {valid_severities}")

    rule = Rule(
        name=body.name,
        topic_pattern=body.topic_pattern,
        condition_type=body.condition_type,
        condition_value=body.condition_value,
        condition_operator=body.condition_operator,
        severity=body.severity,
        slack_channel=body.slack_channel,
        message_template=body.message_template,
        cooldown_seconds=body.cooldown_seconds,
        enabled=body.enabled,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.get("/{rule_id}")
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    return _rule_to_dict(rule)


@router.put("/{rule_id}")
async def update_rule(
    rule_id: int, body: RuleUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    # Validate enum fields if provided
    if body.condition_type is not None:
        valid_types = {"any", "contains", "regex", "json_path", "threshold"}
        if body.condition_type not in valid_types:
            raise HTTPException(400, f"Invalid condition_type. Must be one of: {valid_types}")
    if body.condition_operator is not None:
        valid_operators = {"==", "!=", ">", "<", ">=", "<="}
        if body.condition_operator not in valid_operators:
            raise HTTPException(400, f"Invalid condition_operator. Must be one of: {valid_operators}")
    if body.severity is not None:
        valid_severities = {"info", "warning", "critical"}
        if body.severity not in valid_severities:
            raise HTTPException(400, f"Invalid severity. Must be one of: {valid_severities}")

    for field in [
        "name", "topic_pattern", "condition_type", "condition_value",
        "condition_operator", "severity", "slack_channel", "message_template",
        "cooldown_seconds", "enabled",
    ]:
        value = getattr(body, field)
        if value is not None:
            setattr(rule, field, value)

    await db.commit()
    return _rule_to_dict(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/test")
async def test_rule(
    rule_id: int, body: RuleTest, db: AsyncSession = Depends(get_db)
):
    """Test a rule against a sample message."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    rule_dict = _rule_to_dict(rule)
    match = _test_engine.test_rule(body.topic, body.payload, rule_dict)
    return {
        "matched": match.matched,
        "details": match.details,
        "severity": match.severity,
    }
