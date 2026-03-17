"""MQTT topic management API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Topic, get_session_factory

router = APIRouter(prefix="/api/topics", tags=["topics"])


class TopicCreate(BaseModel):
    topic_pattern: str
    description: str = ""
    enabled: bool = True


class TopicUpdate(BaseModel):
    topic_pattern: str | None = None
    description: str | None = None
    enabled: bool | None = None


async def get_db():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@router.get("")
async def list_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).order_by(Topic.created_at.desc()))
    topics = result.scalars().all()
    return [
        {
            "id": t.id,
            "topic_pattern": t.topic_pattern,
            "description": t.description,
            "enabled": t.enabled,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in topics
    ]


@router.post("", status_code=201)
async def create_topic(body: TopicCreate, db: AsyncSession = Depends(get_db)):
    # Check for duplicate
    result = await db.execute(
        select(Topic).where(Topic.topic_pattern == body.topic_pattern)
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Topic pattern already exists")

    topic = Topic(
        topic_pattern=body.topic_pattern,
        description=body.description,
        enabled=body.enabled,
        created_at=datetime.now(timezone.utc),
    )
    db.add(topic)
    await db.commit()
    return {
        "id": topic.id,
        "topic_pattern": topic.topic_pattern,
        "description": topic.description,
        "enabled": topic.enabled,
        "created_at": topic.created_at.isoformat(),
    }


@router.get("/{topic_id}")
async def get_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(404, "Topic not found")
    return {
        "id": topic.id,
        "topic_pattern": topic.topic_pattern,
        "description": topic.description,
        "enabled": topic.enabled,
        "created_at": topic.created_at.isoformat() if topic.created_at else None,
    }


@router.put("/{topic_id}")
async def update_topic(
    topic_id: int, body: TopicUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(404, "Topic not found")

    if body.topic_pattern is not None:
        topic.topic_pattern = body.topic_pattern
    if body.description is not None:
        topic.description = body.description
    if body.enabled is not None:
        topic.enabled = body.enabled

    await db.commit()
    return {
        "id": topic.id,
        "topic_pattern": topic.topic_pattern,
        "description": topic.description,
        "enabled": topic.enabled,
        "created_at": topic.created_at.isoformat() if topic.created_at else None,
    }


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(404, "Topic not found")
    await db.delete(topic)
    await db.commit()
