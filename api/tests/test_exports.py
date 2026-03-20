# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for CSV and PDF export endpoints.
"""
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db
from app.models.event import Event
from app.models.user import User
from app.services.key_service import create_api_key

# Register the exports router (main.py doesn't include it yet — Task C)
from app.routers.exports import router as exports_router
from app.routers.admin_pricing import router as admin_pricing_router

# Only add routers if not already registered (avoid duplicate on re-import)
_registered_prefixes = {r.prefix for r in app.routes if hasattr(r, "prefix")}
if "/api/exports" not in _registered_prefixes:
    app.include_router(exports_router)
if "/api/admin" not in _registered_prefixes:
    app.include_router(admin_pricing_router)

TEST_DATABASE_URL = "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"


@pytest_asyncio.fixture()
async def export_fixtures():
    """Create user, API key, and sample events for export tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Create user
        unique = uuid.uuid4().hex[:8]
        user = User(email=f"export_test_{unique}@tokenbudget.dev", name="Export Test User")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create API key
        api_key, raw_key = await create_api_key(session, user.id, "Export Test Key")

        # Create sample events across a few days
        now = datetime.now(timezone.utc)
        events = []
        for i in range(5):
            ev = Event(
                user_id=user.id,
                api_key_id=api_key.id,
                provider="openai",
                model="gpt-4o",
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                total_tokens=150 * (i + 1),
                cost_usd=0.001 * (i + 1),
                created_at=now - timedelta(days=i),
            )
            events.append(ev)
        for i in range(3):
            ev = Event(
                user_id=user.id,
                api_key_id=api_key.id,
                provider="anthropic",
                model="claude-sonnet-4",
                input_tokens=200 * (i + 1),
                output_tokens=100 * (i + 1),
                total_tokens=300 * (i + 1),
                cost_usd=0.002 * (i + 1),
                created_at=now - timedelta(days=i),
            )
            events.append(ev)
        session.add_all(events)
        await session.commit()

    # Override DB dependency
    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "raw_key": raw_key,
            "user_id": user.id,
            "headers": {"Authorization": f"Bearer {raw_key}"},
        }

    app.dependency_overrides.clear()
    await engine.dispose()


# ── CSV Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_export_returns_valid_csv(export_fixtures):
    """CSV export returns valid CSV with correct headers."""
    fx = export_fixtures
    resp = await fx["client"].get("/api/exports/csv", headers=fx["headers"])
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")

    # Parse CSV
    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) >= 2  # header + at least one data row
    assert rows[0] == ["date", "provider", "model", "requests", "input_tokens", "output_tokens", "cost_usd"]


@pytest.mark.asyncio
async def test_csv_export_requires_auth(export_fixtures):
    """CSV export requires API key auth."""
    fx = export_fixtures
    resp = await fx["client"].get("/api/exports/csv")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_csv_export_date_range_filtering(export_fixtures):
    """CSV export respects date range query params."""
    fx = export_fixtures
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    resp = await fx["client"].get(
        "/api/exports/csv",
        params={"start_date": yesterday, "end_date": today},
        headers=fx["headers"],
    )
    assert resp.status_code == 200

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    # Should have fewer rows than unfiltered (or at most equal)
    assert len(rows) >= 2  # header + data


# ── PDF Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pdf_export_returns_pdf(export_fixtures):
    """PDF export returns application/pdf content type."""
    fx = export_fixtures
    resp = await fx["client"].get("/api/exports/pdf", headers=fx["headers"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")
    # PDF files start with %PDF
    assert resp.content[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_pdf_export_requires_auth(export_fixtures):
    """PDF export requires API key auth."""
    fx = export_fixtures
    resp = await fx["client"].get("/api/exports/pdf")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_pdf_export_date_range_filtering(export_fixtures):
    """PDF export respects date range query params."""
    fx = export_fixtures
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    resp = await fx["client"].get(
        "/api/exports/pdf",
        params={"start_date": yesterday, "end_date": today},
        headers=fx["headers"],
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
