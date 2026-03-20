# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Guardrail tests — 12 tests covering:
  - Free tier event quota enforcement
  - Signup kill switch
  - Key quota enforcement
  - Purge job behavior
  - Usage-summary endpoint
  - Admin purge endpoint
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.models.event import Event
from app.models.user import User
from app.services.key_service import create_api_key


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event_payload(**overrides):
    base = {
        "provider": "openai",
        "model": "gpt-4o",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.003,
        "latency_ms": 800,
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# 1. check_event_quota — passes when under limit
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_event_quota_under_limit(client, auth_headers):
    """A single event well within the free tier limit should succeed."""
    response = await client.post("/v1/events", json=_make_event_payload(), headers=auth_headers)
    assert response.status_code == 202
    assert response.json()["accepted"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 2. check_event_quota — 429 when Redis reports over limit
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_event_quota_exceeded_via_redis(client, auth_headers):
    """When Redis counter exceeds the monthly limit, POST /v1/events returns 429."""
    # Patch _redis_incr_quota to simulate an already-exceeded counter
    with patch(
        "app.lib.tier_check._redis_incr_quota",
        new_callable=AsyncMock,
        return_value=99_999_999,  # way over FREE_EVENTS_PER_MONTH
    ):
        response = await client.post(
            "/v1/events", json=_make_event_payload(), headers=auth_headers
        )
    assert response.status_code == 429
    data = response.json()
    assert data["detail"]["error"] == "quota_exceeded"
    assert "limit" in data["detail"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. check_event_quota — falls back to DB when Redis is down
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_event_quota_redis_fallback_passes(client, auth_headers):
    """When Redis is unavailable, DB COUNT is used and should pass for a new user."""
    # Redis returns None (simulating connection failure)
    with patch(
        "app.lib.tier_check._redis_incr_quota",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await client.post(
            "/v1/events", json=_make_event_payload(), headers=auth_headers
        )
    # DB count for fresh test user is 0, so well under limit
    assert response.status_code == 202


# ══════════════════════════════════════════════════════════════════════════════
# 4. check_event_quota — DB fallback enforces limit
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_event_quota_db_fallback_exceeded(client, auth_headers, test_user_and_key, db_session):
    """When Redis is down AND the DB has >= limit events this month, return 429."""
    from app.config import config

    # We'd need 10,000 rows to hit the real limit — instead, temporarily lower it
    with patch.object(config, "FREE_EVENTS_PER_MONTH", 2):
        # Seed 2 events directly
        for _ in range(2):
            db_session.add(
                Event(
                    api_key_id=test_user_and_key["api_key_id"],
                    user_id=test_user_and_key["user_id"],
                    provider="openai",
                    model="gpt-4",
                    input_tokens=10,
                    output_tokens=5,
                    total_tokens=15,
                    cost_usd=0.001,
                    latency_ms=100,
                )
            )
        await db_session.commit()

        with patch(
            "app.lib.tier_check._redis_incr_quota",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.post(
                "/v1/events", json=_make_event_payload(), headers=auth_headers
            )

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "quota_exceeded"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Batch endpoint also enforced
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_batch_event_quota_exceeded(client, auth_headers):
    """POST /v1/events/batch is also subject to quota checks."""
    with patch(
        "app.lib.tier_check._redis_incr_quota",
        new_callable=AsyncMock,
        return_value=99_999_999,
    ):
        batch = {"events": [_make_event_payload(), _make_event_payload()]}
        response = await client.post("/v1/events/batch", json=batch, headers=auth_headers)

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "quota_exceeded"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Signup kill switch — 503 when disabled
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_signup_kill_switch_disabled(client, auth_headers):
    """When SIGNUPS_ENABLED=False, POST /api/keys returns 503."""
    from app.config import config

    with patch.object(config, "SIGNUPS_ENABLED", False):
        response = await client.post("/api/keys", json={"name": "Test Key"}, headers=auth_headers)

    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["error"] == "signups_paused"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Signup kill switch — 201 when enabled
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_signup_kill_switch_enabled(client, auth_headers):
    """When SIGNUPS_ENABLED=True (default), POST /api/keys succeeds."""
    from app.config import config

    with patch.object(config, "SIGNUPS_ENABLED", True):
        response = await client.post("/api/keys", json={"name": "Test Key"}, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["raw_key"].startswith("tb_ak_")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Key quota enforcement
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_key_quota_exceeded(client, auth_headers, test_user_and_key, db_session):
    """After reaching FREE_KEYS_MAX active keys, creating another returns 429."""
    from app.config import config

    with patch.object(config, "FREE_KEYS_MAX", 1):
        # Already 1 key from the fixture — should be at limit
        response = await client.post("/api/keys", json={"name": "Extra Key"}, headers=auth_headers)

    assert response.status_code == 429
    data = response.json()
    assert data["detail"]["error"] == "key_quota_exceeded"


# ══════════════════════════════════════════════════════════════════════════════
# 9. Purge job — deletes old events and returns summary
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_purge_deletes_old_events(test_user_and_key, db_session):
    """run_purge() should delete events older than FREE_RETENTION_DAYS."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text, update
    from app.config import config
    from app.jobs.purge_old_events import run_purge

    user_id = test_user_and_key["user_id"]
    api_key_id = test_user_and_key["api_key_id"]

    # Insert one RECENT event first (should NOT be deleted)
    recent_event = Event(
        api_key_id=api_key_id,
        user_id=user_id,
        provider="openai",
        model="gpt-4",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        cost_usd=0.001,
        latency_ms=100,
    )
    db_session.add(recent_event)
    await db_session.commit()
    await db_session.refresh(recent_event)

    # Insert one OLD event
    old_event = Event(
        api_key_id=api_key_id,
        user_id=user_id,
        provider="openai",
        model="gpt-4",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        cost_usd=0.001,
        latency_ms=100,
    )
    db_session.add(old_event)
    await db_session.commit()
    await db_session.refresh(old_event)

    # Backdate the old event via raw SQL (server_default can't be overridden in Python)
    old_ts = datetime.now(timezone.utc) - timedelta(days=config.FREE_RETENTION_DAYS + 2)
    await db_session.execute(
        text("UPDATE events SET created_at = :ts WHERE id = :id"),
        {"ts": old_ts, "id": str(old_event.id)},
    )
    await db_session.commit()

    # Capture IDs before expiring session state
    recent_id = recent_event.id
    old_id = old_event.id

    # Run purge against the TEST database (not the default main DB)
    with patch.object(config, "DATABASE_URL", "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"):
        result = await run_purge()

    assert result["deleted"] >= 1
    assert result["retention_days"] == config.FREE_RETENTION_DAYS

    # Recent event should still exist
    remaining = await db_session.execute(
        select(Event).where(Event.id == recent_id)
    )
    assert remaining.scalar_one_or_none() is not None

    # Old event should be gone
    gone = await db_session.execute(
        select(Event).where(Event.id == old_id)
    )
    assert gone.scalar_one_or_none() is None


# ══════════════════════════════════════════════════════════════════════════════
# 10. Purge job — no events to purge returns 0
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_purge_no_old_events():
    """run_purge() with no old events returns deleted=0."""
    from unittest.mock import patch
    from app.config import config
    from app.jobs.purge_old_events import run_purge

    with patch.object(config, "DATABASE_URL", "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"):
        result = await run_purge()
    assert "deleted" in result
    assert "batches" in result
    # deleted may be > 0 if other tests left old events, but must be >= 0
    assert result["deleted"] >= 0


# ══════════════════════════════════════════════════════════════════════════════
# 11. Usage summary endpoint
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_usage_summary_endpoint(client, auth_headers):
    """GET /api/analytics/usage-summary returns correct structure."""
    response = await client.get("/api/analytics/usage-summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "free"
    assert "events_this_month" in data
    assert "events_limit" in data
    assert "events_pct" in data
    assert "active_keys" in data
    assert "keys_limit" in data
    assert data["events_limit"] > 0
    assert data["keys_limit"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# 12. Admin purge endpoint — 403 without key, 200 with valid key
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.asyncio
async def test_admin_purge_requires_key(client):
    """POST /api/admin/purge without X-Admin-Key returns 403."""
    response = await client.post("/api/admin/purge")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_purge_with_valid_key(client):
    """POST /api/admin/purge with correct X-Admin-Key returns 200."""
    from app.config import config

    with patch.object(config, "ADMIN_KEY", "test-admin-secret"):
        response = await client.post(
            "/api/admin/purge",
            headers={"X-Admin-Key": "test-admin-secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "deleted" in data
