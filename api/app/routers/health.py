# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.config import config
import redis.asyncio as aioredis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    # Check DB
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Redis
    redis_status = "connected"
    try:
        r = aioredis.from_url(config.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "unavailable"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": "0.2.0",
        "db": db_status,
        "redis": redis_status,
    }


@router.get("/api/auth/config")
async def auth_config():
    """Public endpoint — tells the frontend which auth mode is active."""
    return {
        "auth_mode": config.AUTH_MODE,
        "clerk_publishable_key": config.CLERK_PUBLISHABLE_KEY if config.AUTH_MODE == "clerk" else None,
    }
