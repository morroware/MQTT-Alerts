"""Dashboard and system health API routes."""

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AlertLog, Message, Rule, Topic, get_session_factory

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def get_db():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(hours=24)

    # Topic count
    result = await db.execute(select(func.count(Topic.id)))
    topic_count = result.scalar() or 0

    # Enabled topic count
    result = await db.execute(
        select(func.count(Topic.id)).where(Topic.enabled == True)  # noqa: E712
    )
    active_topic_count = result.scalar() or 0

    # Rule count
    result = await db.execute(select(func.count(Rule.id)))
    rule_count = result.scalar() or 0

    # Messages in last hour
    result = await db.execute(
        select(func.count(Message.id)).where(Message.received_at >= hour_ago)
    )
    messages_last_hour = result.scalar() or 0

    # Messages in last 24h
    result = await db.execute(
        select(func.count(Message.id)).where(Message.received_at >= day_ago)
    )
    messages_last_24h = result.scalar() or 0

    # Alerts in last 24h
    result = await db.execute(
        select(func.count(AlertLog.id)).where(AlertLog.sent_at >= day_ago)
    )
    alerts_last_24h = result.scalar() or 0

    # Alerts by severity in last 24h
    result = await db.execute(
        select(AlertLog.severity, func.count(AlertLog.id))
        .where(AlertLog.sent_at >= day_ago)
        .group_by(AlertLog.severity)
    )
    severity_counts = {row[0]: row[1] for row in result.all()}

    return {
        "topics": {"total": topic_count, "active": active_topic_count},
        "rules": {"total": rule_count},
        "messages": {"last_hour": messages_last_hour, "last_24h": messages_last_24h},
        "alerts": {
            "last_24h": alerts_last_24h,
            "by_severity": severity_counts,
        },
    }


@router.get("/recent-alerts")
async def get_recent_alerts(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    """Get recent alerts."""
    result = await db.execute(
        select(AlertLog).order_by(AlertLog.sent_at.desc()).limit(limit)
    )
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "rule_id": a.rule_id,
            "rule_name": a.rule_name,
            "topic": a.topic,
            "severity": a.severity,
            "slack_response": a.slack_response,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
        }
        for a in alerts
    ]


@router.get("/system-health")
async def get_system_health():
    """Get system health status."""
    # Check alert service health
    health_file = Path("/tmp/mqtt-alert-service.health")
    alert_service_status = "unknown"
    mqtt_connected = False
    if health_file.exists():
        try:
            data = json.loads(health_file.read_text())
            alert_service_status = data.get("status", "unknown")
            mqtt_connected = data.get("mqtt_connected", False)
        except (json.JSONDecodeError, OSError):
            alert_service_status = "error"
    else:
        alert_service_status = "stopped"

    # Check disk usage
    disk = shutil.disk_usage("/")
    disk_percent = round((disk.used / disk.total) * 100, 1)

    return {
        "alert_service": alert_service_status,
        "mqtt_connected": mqtt_connected,
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk_percent,
        },
    }
