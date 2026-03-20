# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tier enforcement helpers.

All Redis operations fail gracefully — if Redis is unavailable we fall back
to a DB COUNT so the system never blocks a request due to a Redis outage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.api_key import ApiKey
from app.models.event import Event

logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Internal Redis helpers
# ---------------------------------------------------------------------------

async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(config.REDIS_URL, decode_responses=True)


async def _redis_incr_quota(key: str, ttl_seconds: int) -> int | None:
    """INCR the quota key; set expiry on first write. Returns new value or None on error."""
    try:
        r = await _get_redis()
        val = await r.incr(key)
        if val == 1:
            # First write — set TTL to end of month (approx 32 days is fine)
            await r.expire(key, ttl_seconds)
        await r.aclose()
        return val
    except Exception as exc:
        logger.warning("Redis quota INCR failed (%s): %s", key, exc)
        return None


async def _redis_get_quota(key: str) -> int | None:
    """GET the quota counter. Returns int or None on error/miss."""
    try:
        r = await _get_redis()
        val = await r.get(key)
        await r.aclose()
        return int(val) if val is not None else None
    except Exception as exc:
        logger.warning("Redis quota GET failed (%s): %s", key, exc)
        return None


# ---------------------------------------------------------------------------
# Event quota
# ---------------------------------------------------------------------------

async def check_event_quota(db: AsyncSession, user_id, tier: str = "free") -> None:
    """
    Increment and check the monthly event quota for *user_id*.

    Raises HTTP 429 if the user is over their limit.
    Falls back to DB COUNT if Redis is unavailable.
    """
    now = datetime.now(timezone.utc)
    month_key = f"quota:{user_id}:{now.year}-{now.month:02d}"

    # TTL: seconds until end of current month (rough: 32 days from first write)
    ttl = 32 * 24 * 3600

    limits = config.get_tier_limits()
    monthly_limit = limits["events_per_month"]

    # Try Redis first (O(1))
    redis_count = await _redis_incr_quota(month_key, ttl)

    if redis_count is not None:
        if redis_count > monthly_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": (
                        f"Monthly event quota of {monthly_limit:,} exceeded."
                    ),
                    "current": redis_count,
                    "limit": monthly_limit,
                },
            )
        return  # within quota

    # Redis miss/error — fall back to DB COUNT
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Event.id)).where(
            Event.user_id == user_id,
            Event.created_at >= month_start,
        )
    )
    db_count = result.scalar() or 0

    if db_count >= monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "message": (
                    f"Monthly event quota of {monthly_limit:,} exceeded."
                ),
                "current": db_count,
                "limit": monthly_limit,
            },
        )


# ---------------------------------------------------------------------------
# API key creation quota
# ---------------------------------------------------------------------------

async def check_key_quota(db: AsyncSession, user_id, tier: str = "free") -> None:
    """
    Check whether *user_id* has reached their key creation limit.

    Raises HTTP 429 if the user is at or over their limit.
    """
    limits = config.get_tier_limits()
    keys_max = limits["keys_max"]

    result = await db.execute(
        select(func.count(ApiKey.id)).where(
            ApiKey.user_id == user_id,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    active_keys = result.scalar() or 0

    if active_keys >= keys_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "key_quota_exceeded",
                "message": (
                    f"Maximum of {keys_max} active API keys reached. "
                    f"Delete an existing key to create a new one."
                ),
                "current": active_keys,
                "limit": keys_max,
            },
        )
