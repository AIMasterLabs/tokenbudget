# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.api_key import ApiKey
from app.models.event import Event
from app.schemas.events import EventCreate


async def create_event(db: AsyncSession, event_data: EventCreate, api_key: ApiKey) -> Event:
    """Create a single event row from EventCreate schema and ApiKey context."""
    event = Event(
        api_key_id=api_key.id,
        user_id=api_key.user_id,
        team_id=api_key.team_id,
        provider=event_data.provider,
        model=event_data.model,
        input_tokens=event_data.input_tokens,
        output_tokens=event_data.output_tokens,
        reasoning_tokens=event_data.reasoning_tokens or 0,
        total_tokens=event_data.total_tokens,
        cost_usd=event_data.cost_usd,
        latency_ms=event_data.latency_ms,
        tags=event_data.tags,
        metadata_=event_data.metadata,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def create_events_batch(
    db: AsyncSession, events: list[EventCreate], api_key: ApiKey
) -> list[Event]:
    """Bulk insert multiple events using a single INSERT statement."""
    if not events:
        return []

    rows = [
        {
            "api_key_id": api_key.id,
            "user_id": api_key.user_id,
            "team_id": api_key.team_id,
            "provider": e.provider,
            "model": e.model,
            "input_tokens": e.input_tokens,
            "output_tokens": e.output_tokens,
            "reasoning_tokens": e.reasoning_tokens or 0,
            "total_tokens": e.total_tokens,
            "cost_usd": e.cost_usd,
            "latency_ms": e.latency_ms,
            "tags": e.tags,
            "metadata": e.metadata,
        }
        for e in events
    ]

    stmt = pg_insert(Event).returning(Event)
    result = await db.execute(stmt, rows)
    inserted = result.scalars().all()
    await db.commit()
    return inserted
