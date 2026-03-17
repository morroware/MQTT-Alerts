"""Message history and live feed API routes."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import Message, get_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/messages", tags=["messages"])


async def get_db():
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@router.get("")
async def list_messages(
    topic: str = Query(None, description="Filter by topic"),
    search: str = Query(None, description="Search in payload"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated message history."""
    query = select(Message).order_by(Message.received_at.desc())

    if topic:
        query = query.where(Message.topic == topic)
    if search:
        query = query.where(Message.payload.contains(search))

    # Get total count
    count_query = select(func.count(Message.id))
    if topic:
        count_query = count_query.where(Message.topic == topic)
    if search:
        count_query = count_query.where(Message.payload.contains(search))
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get page
    result = await db.execute(query.offset(offset).limit(limit))
    messages = result.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "messages": [
            {
                "id": m.id,
                "topic": m.topic,
                "payload": m.payload,
                "qos": m.qos,
                "retained": m.retained,
                "received_at": m.received_at.isoformat() if m.received_at else None,
            }
            for m in messages
        ],
    }


@router.get("/topics")
async def list_message_topics(db: AsyncSession = Depends(get_db)):
    """Get distinct topics that have messages."""
    result = await db.execute(
        select(Message.topic, func.count(Message.id).label("count"))
        .group_by(Message.topic)
        .order_by(func.count(Message.id).desc())
    )
    return [{"topic": row[0], "count": row[1]} for row in result.all()]


# WebSocket connections for live feed
_live_connections: set[WebSocket] = set()


async def broadcast_message(topic: str, payload: str, qos: int):
    """Broadcast a message to all live feed WebSocket clients."""
    data = json.dumps({
        "topic": topic,
        "payload": payload,
        "qos": qos,
    })
    disconnected = set()
    for ws in _live_connections:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    _live_connections -= disconnected


@router.websocket("/live")
async def live_feed(websocket: WebSocket):
    """WebSocket endpoint for real-time MQTT message stream."""
    await websocket.accept()
    _live_connections.add(websocket)
    logger.info("Live feed client connected (%d total)", len(_live_connections))

    try:
        while True:
            # Keep connection alive; client can send filter commands
            data = await websocket.receive_text()
            # Could handle filter commands here in the future
    except WebSocketDisconnect:
        pass
    finally:
        _live_connections.discard(websocket)
        logger.info("Live feed client disconnected (%d total)", len(_live_connections))
