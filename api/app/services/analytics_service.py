# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, cast, String
from app.models.event import Event
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    ModelBreakdown,
    UserBreakdown,
    TimeseriesPoint,
    TagBreakdown,
)


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def get_summary(
    db: AsyncSession,
    user_id,
    team_id=None,
    days: int = 30,
) -> AnalyticsSummary:
    since = _since(days)

    q = select(
        func.coalesce(func.sum(Event.cost_usd), 0).label("total_cost_usd"),
        func.count(Event.id).label("total_requests"),
        func.coalesce(func.sum(Event.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(Event.output_tokens), 0).label("total_output_tokens"),
        func.coalesce(func.sum(Event.reasoning_tokens), 0).label("total_reasoning_tokens"),
        func.coalesce(func.avg(Event.cost_usd), 0).label("avg_cost_per_request"),
        func.coalesce(func.avg(Event.latency_ms), 0).label("avg_latency_ms"),
    ).where(Event.created_at >= since)

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    else:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    row = result.one()

    return AnalyticsSummary(
        total_cost_usd=float(row.total_cost_usd),
        total_requests=int(row.total_requests),
        total_input_tokens=int(row.total_input_tokens),
        total_output_tokens=int(row.total_output_tokens),
        total_reasoning_tokens=int(row.total_reasoning_tokens),
        avg_cost_per_request=float(row.avg_cost_per_request),
        avg_latency_ms=float(row.avg_latency_ms),
    )


async def get_by_model(
    db: AsyncSession,
    user_id,
    team_id=None,
    days: int = 30,
) -> list[ModelBreakdown]:
    since = _since(days)

    q = (
        select(
            Event.model,
            func.sum(Event.cost_usd).label("total_cost_usd"),
            func.count(Event.id).label("request_count"),
        )
        .where(Event.created_at >= since)
        .group_by(Event.model)
        .order_by(func.sum(Event.cost_usd).desc())
    )

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    else:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    rows = result.all()

    total_cost = sum(float(r.total_cost_usd) for r in rows)

    breakdown = []
    for r in rows:
        cost = float(r.total_cost_usd)
        pct = (cost / total_cost * 100) if total_cost > 0 else 0.0
        breakdown.append(
            ModelBreakdown(
                model=r.model,
                total_cost_usd=cost,
                request_count=int(r.request_count),
                percentage=round(pct, 2),
            )
        )
    return breakdown


async def get_by_user(
    db: AsyncSession,
    team_id=None,
    user_id=None,
    days: int = 30,
) -> list[UserBreakdown]:
    since = _since(days)

    q = (
        select(
            Event.user_id,
            User.email,
            func.sum(Event.cost_usd).label("total_cost_usd"),
            func.count(Event.id).label("request_count"),
        )
        .join(User, User.id == Event.user_id)
        .where(Event.created_at >= since)
        .group_by(Event.user_id, User.email)
        .order_by(func.sum(Event.cost_usd).desc())
    )

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    elif user_id is not None:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    rows = result.all()

    return [
        UserBreakdown(
            user_id=str(r.user_id),
            email=r.email,
            total_cost_usd=float(r.total_cost_usd),
            request_count=int(r.request_count),
        )
        for r in rows
    ]


async def get_timeseries(
    db: AsyncSession,
    user_id,
    team_id=None,
    days: int = 30,
    granularity: str = "daily",
) -> list[TimeseriesPoint]:
    since = _since(days)

    # Map granularity to date_trunc unit
    trunc_map = {"daily": "day", "hourly": "hour", "weekly": "week"}
    trunc_unit = trunc_map.get(granularity, "day")

    bucket = func.date_trunc(trunc_unit, Event.created_at).label("bucket")

    q = (
        select(
            bucket,
            func.sum(Event.cost_usd).label("cost_usd"),
            func.count(Event.id).label("request_count"),
        )
        .where(Event.created_at >= since)
        .group_by(bucket)
        .order_by(bucket)
    )

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    else:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    rows = result.all()

    return [
        TimeseriesPoint(
            timestamp=r.bucket,
            cost_usd=float(r.cost_usd),
            request_count=int(r.request_count),
        )
        for r in rows
    ]


async def get_by_tag(
    db: AsyncSession,
    user_id,
    tag_key: str,
    team_id=None,
    days: int = 30,
) -> list[TagBreakdown]:
    since = _since(days)

    # Use PostgreSQL JSON extraction: tags->>'key'
    tag_value_expr = func.jsonb_extract_path_text(
        Event.tags.cast(text("jsonb")), tag_key
    ).label("tag_value")

    q = (
        select(
            tag_value_expr,
            func.sum(Event.cost_usd).label("total_cost_usd"),
            func.count(Event.id).label("request_count"),
        )
        .where(Event.created_at >= since)
        .where(Event.tags.isnot(None))
        .where(
            func.jsonb_extract_path_text(Event.tags.cast(text("jsonb")), tag_key).isnot(None)
        )
        .group_by(tag_value_expr)
        .order_by(func.sum(Event.cost_usd).desc())
    )

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    else:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    rows = result.all()

    return [
        TagBreakdown(
            tag_value=r.tag_value,
            total_cost_usd=float(r.total_cost_usd),
            request_count=int(r.request_count),
        )
        for r in rows
    ]
