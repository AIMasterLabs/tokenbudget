# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for price change detection, formatting, storage, and endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db
from app.routers.price_changes import router as price_changes_router
from app.services.price_monitor import (
    detect_price_changes,
    store_price_changes,
    format_price_change_email,
    format_price_change_slack,
)

# Register the router for testing (main.py is not modified per task requirements)
_registered = any(
    getattr(r, "path", "") == "/api/price-changes" for r in app.routes
)
if not _registered:
    app.include_router(price_changes_router)


# ---------------------------------------------------------------------------
# Unit tests — detect_price_changes
# ---------------------------------------------------------------------------

class TestDetectPriceChanges:
    def test_detects_input_price_change(self):
        old = {"gpt-4o": (0.0025, 0.010)}
        new = {"gpt-4o": (0.005, 0.010)}
        changes = detect_price_changes(old, new)
        assert len(changes) == 1
        assert changes[0]["model"] == "gpt-4o"
        assert changes[0]["old_input_price"] == 0.0025
        assert changes[0]["new_input_price"] == 0.005

    def test_detects_output_price_change(self):
        old = {"claude-3-5-sonnet": (0.003, 0.015)}
        new = {"claude-3-5-sonnet": (0.003, 0.020)}
        changes = detect_price_changes(old, new)
        assert len(changes) == 1
        assert changes[0]["old_output_price"] == 0.015
        assert changes[0]["new_output_price"] == 0.020

    def test_no_changes_when_prices_same(self):
        prices = {
            "gpt-4o": (0.0025, 0.010),
            "claude-3-5-sonnet": (0.003, 0.015),
        }
        changes = detect_price_changes(prices, prices)
        assert len(changes) == 0

    def test_detects_new_model(self):
        old = {"gpt-4o": (0.0025, 0.010)}
        new = {"gpt-4o": (0.0025, 0.010), "gpt-5": (0.01, 0.03)}
        changes = detect_price_changes(old, new)
        assert len(changes) == 1
        assert changes[0]["model"] == "gpt-5"
        assert changes[0]["old_input_price"] == 0.0
        assert changes[0]["new_input_price"] == 0.01

    def test_detects_removed_model(self):
        old = {"gpt-4o": (0.0025, 0.010), "gpt-4": (0.03, 0.06)}
        new = {"gpt-4o": (0.0025, 0.010)}
        changes = detect_price_changes(old, new)
        assert len(changes) == 1
        assert changes[0]["model"] == "gpt-4"
        assert changes[0]["new_input_price"] == 0.0

    def test_multiple_changes(self):
        old = {
            "gpt-4o": (0.0025, 0.010),
            "claude-3-5-sonnet": (0.003, 0.015),
        }
        new = {
            "gpt-4o": (0.005, 0.020),
            "claude-3-5-sonnet": (0.002, 0.010),
        }
        changes = detect_price_changes(old, new)
        assert len(changes) == 2

    def test_infers_openai_provider(self):
        old = {"gpt-4o": (0.0025, 0.010)}
        new = {"gpt-4o": (0.005, 0.010)}
        changes = detect_price_changes(old, new)
        assert changes[0]["provider"] == "openai"

    def test_infers_anthropic_provider(self):
        old = {"claude-3-5-sonnet": (0.003, 0.015)}
        new = {"claude-3-5-sonnet": (0.002, 0.015)}
        changes = detect_price_changes(old, new)
        assert changes[0]["provider"] == "anthropic"


# ---------------------------------------------------------------------------
# Unit tests — formatting
# ---------------------------------------------------------------------------

class TestFormatEmail:
    def test_email_includes_model_name(self):
        changes = [{
            "provider": "openai",
            "model": "gpt-4o",
            "old_input_price": 0.0025,
            "new_input_price": 0.005,
            "old_output_price": 0.010,
            "new_output_price": 0.010,
        }]
        html = format_price_change_email(changes)
        assert "gpt-4o" in html

    def test_email_includes_percentage(self):
        changes = [{
            "provider": "openai",
            "model": "gpt-4o",
            "old_input_price": 0.0025,
            "new_input_price": 0.005,
            "old_output_price": 0.010,
            "new_output_price": 0.010,
        }]
        html = format_price_change_email(changes)
        # 0.0025 -> 0.005 = +100%
        assert "+100.00%" in html

    def test_email_shows_direction(self):
        changes = [{
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "old_input_price": 0.003,
            "new_input_price": 0.002,
            "old_output_price": 0.015,
            "new_output_price": 0.015,
        }]
        html = format_price_change_email(changes)
        assert "DOWN" in html

    def test_email_empty_changes(self):
        html = format_price_change_email([])
        assert "No price changes" in html


class TestFormatSlack:
    def test_slack_includes_model_name(self):
        changes = [{
            "provider": "openai",
            "model": "gpt-4o",
            "old_input_price": 0.0025,
            "new_input_price": 0.005,
            "old_output_price": 0.010,
            "new_output_price": 0.020,
        }]
        msg = format_price_change_slack(changes)
        assert "gpt-4o" in msg
        assert "UP" in msg

    def test_slack_empty_changes(self):
        msg = format_price_change_slack([])
        assert "No price changes" in msg


# ---------------------------------------------------------------------------
# Async tests — store_price_changes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_store_price_changes(db_session):
    """store_price_changes persists records to the database."""
    changes = [
        {
            "provider": "openai",
            "model": "gpt-4o",
            "old_input_price": 0.0025,
            "new_input_price": 0.005,
            "old_output_price": 0.010,
            "new_output_price": 0.020,
        },
        {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "old_input_price": 0.003,
            "new_input_price": 0.002,
            "old_output_price": 0.015,
            "new_output_price": 0.010,
        },
    ]
    records = await store_price_changes(changes, db_session)
    assert len(records) == 2
    assert records[0].model == "gpt-4o"
    assert records[0].provider == "openai"
    assert records[0].new_input_price == 0.005
    assert records[0].notified is False
    assert records[1].model == "claude-3-5-sonnet"
    assert records[1].id is not None


# ---------------------------------------------------------------------------
# Integration tests — endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_price_changes_empty(client, auth_headers):
    """GET /api/price-changes returns empty list when no changes exist."""
    resp = await client.get("/api/price-changes", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_price_changes_returns_recent(client, auth_headers, db_session):
    """GET /api/price-changes returns stored changes."""
    changes = [{
        "provider": "openai",
        "model": "gpt-4o",
        "old_input_price": 0.0025,
        "new_input_price": 0.005,
        "old_output_price": 0.010,
        "new_output_price": 0.020,
    }]
    await store_price_changes(changes, db_session)

    resp = await client.get("/api/price-changes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    found = [d for d in data if d["model"] == "gpt-4o"]
    assert len(found) >= 1
    assert found[0]["new_input_price"] == 0.005


@pytest.mark.asyncio
async def test_price_changes_require_auth(client):
    """Unauthenticated requests to /api/price-changes return 401."""
    resp = await client.get("/api/price-changes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_check_requires_admin_key(client, auth_headers):
    """GET /api/price-changes/check without admin key returns 403."""
    resp = await client.get("/api/price-changes/check", headers=auth_headers)
    # Either 403 (admin key set but missing) or 503 (admin key not configured)
    assert resp.status_code in (403, 503)
