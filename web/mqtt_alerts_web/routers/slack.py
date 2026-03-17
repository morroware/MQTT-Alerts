"""Slack configuration and testing API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SlackSettings, get_session_factory

router = APIRouter(prefix="/api/settings/slack", tags=["slack"])

# Runtime Slack notifier instance — set by main.py on startup
_notifier = None


def set_notifier(notifier):
    global _notifier
    _notifier = notifier


class SlackSettingsUpdate(BaseModel):
    bot_token: str
    default_channel: str = "#alerts"
    rate_limit: int = 10


class SlackTestRequest(BaseModel):
    channel: str


async def get_db():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@router.get("")
async def get_slack_settings(db: AsyncSession = Depends(get_db)):
    """Get current Slack configuration."""
    result = await db.execute(select(SlackSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        return {
            "bot_token_set": False,
            "default_channel": "#alerts",
            "rate_limit": 10,
            "connected": False,
        }

    # Validate current token
    connected = False
    identity = ""
    if _notifier and settings.bot_token:
        _notifier.update_token(settings.bot_token)
        connected, identity = _notifier.validate()

    return {
        "bot_token_set": bool(settings.bot_token),
        "bot_token_preview": settings.bot_token[:12] + "..." if settings.bot_token else "",
        "default_channel": settings.default_channel,
        "rate_limit": settings.rate_limit,
        "connected": connected,
        "identity": identity,
    }


@router.put("")
async def update_slack_settings(
    body: SlackSettingsUpdate, db: AsyncSession = Depends(get_db)
):
    """Update Slack configuration."""
    result = await db.execute(select(SlackSettings).limit(1))
    settings = result.scalar_one_or_none()

    if settings:
        settings.bot_token = body.bot_token
        settings.default_channel = body.default_channel
        settings.rate_limit = body.rate_limit
        settings.updated_at = datetime.now(timezone.utc)
    else:
        settings = SlackSettings(
            bot_token=body.bot_token,
            default_channel=body.default_channel,
            rate_limit=body.rate_limit,
        )
        db.add(settings)

    await db.commit()

    # Update runtime notifier
    connected = False
    identity = ""
    if _notifier:
        _notifier.update_token(body.bot_token)
        _notifier.default_channel = body.default_channel
        _notifier.rate_limit = body.rate_limit
        if body.bot_token:
            connected, identity = _notifier.validate()

    return {
        "bot_token_set": bool(body.bot_token),
        "default_channel": body.default_channel,
        "rate_limit": body.rate_limit,
        "connected": connected,
        "identity": identity,
    }


@router.post("/test")
async def test_slack(body: SlackTestRequest):
    """Send a test message to Slack."""
    if not _notifier:
        raise HTTPException(500, "Slack notifier not initialized")

    ok, response = _notifier.send_test_message(body.channel)
    if not ok:
        raise HTTPException(400, f"Test failed: {response}")

    return {"success": True, "response": response}


@router.get("/channels")
async def list_slack_channels():
    """List Slack channels the bot can access."""
    if not _notifier:
        raise HTTPException(500, "Slack notifier not initialized")

    ok, channels = _notifier.list_channels()
    if not ok:
        raise HTTPException(400, "Failed to list channels — check bot token and scopes")

    return {"channels": channels}
