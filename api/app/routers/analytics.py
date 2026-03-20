# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import config
from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.event import Event
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsSummary,
    ModelBreakdown,
    UserBreakdown,
    TimeseriesPoint,
    TagBreakdown,
    UsageSummary,
)
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _parse_period(period: str) -> int:
    """Parse period string like '7d', '30d', '90d' to integer days."""
    period = period.strip().lower()
    if period.endswith("d"):
        try:
            return int(period[:-1])
        except ValueError:
            pass
    # fallback: try parsing as plain int
    try:
        return int(period)
    except ValueError:
        return 30


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    period: str = Query(default="30d"),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    days = _parse_period(period)
    return await analytics_service.get_summary(db, user_id=user.id, days=days)


@router.get("/by-model", response_model=list[ModelBreakdown])
async def get_by_model(
    period: str = Query(default="30d"),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    days = _parse_period(period)
    return await analytics_service.get_by_model(db, user_id=user.id, days=days)


@router.get("/by-user", response_model=list[UserBreakdown])
async def get_by_user(
    period: str = Query(default="30d"),
    team_id: str | None = Query(default=None),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    days = _parse_period(period)
    return await analytics_service.get_by_user(db, team_id=team_id, user_id=user.id, days=days)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
async def get_timeseries(
    period: str = Query(default="30d"),
    granularity: str = Query(default="daily"),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    days = _parse_period(period)
    return await analytics_service.get_timeseries(
        db, user_id=user.id, days=days, granularity=granularity
    )


@router.get("/usage-summary", response_model=UsageSummary)
async def get_usage_summary(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Return current month usage vs tier limits for the authenticated user."""
    _, user = auth
    tier = "free"  # All users are free tier until billing is implemented
    limits = config.get_tier_limits(tier)

    # Events this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    events_result = await db.execute(
        select(func.count(Event.id)).where(
            Event.user_id == user.id,
            Event.created_at >= month_start,
        )
    )
    events_this_month = events_result.scalar() or 0

    # Active keys
    keys_result = await db.execute(
        select(func.count(ApiKey.id)).where(
            ApiKey.user_id == user.id,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    active_keys = keys_result.scalar() or 0

    events_limit = limits["events_per_month"]
    keys_limit = limits["keys_max"]

    return UsageSummary(
        tier=tier,
        events_this_month=events_this_month,
        events_limit=events_limit,
        events_pct=round(events_this_month / events_limit * 100, 2) if events_limit else 0.0,
        active_keys=active_keys,
        keys_limit=keys_limit,
        keys_pct=round(active_keys / keys_limit * 100, 2) if keys_limit else 0.0,
        retention_days=limits["retention_days"],
        projects_limit=limits["projects_max"],
    )


@router.get("/by-tag", response_model=list[TagBreakdown])
async def get_by_tag(
    period: str = Query(default="30d"),
    tag_key: str = Query(..., description="The tag key to group by"),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    days = _parse_period(period)
    return await analytics_service.get_by_tag(db, user_id=user.id, tag_key=tag_key, days=days)
