# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Test configuration.

We use function-scoped fixtures throughout to avoid asyncpg/asyncio event loop
mismatch issues between pytest-asyncio's per-test loops and module/session
scoped async fixtures.

Tables are created once at the start of the session via a synchronous setup.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.models import User, ApiKey  # noqa: ensure all models are imported
from app.services.key_service import create_api_key

TEST_DATABASE_URL = "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"


def pytest_configure(config):
    """Create tables synchronously before the test session starts."""
    import asyncio

    async def _setup():
        engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_setup())


@pytest_asyncio.fixture()
async def db_session():
    """Provide a fresh AsyncSession per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def test_user_and_key(db_session):
    """Create a unique test user + API key for this test."""
    import uuid
    unique = uuid.uuid4().hex[:8]
    user = User(email=f"testuser_{unique}@tokenbudget.dev", name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    api_key, raw_key = await create_api_key(db_session, user.id, "Test Key")
    return {
        "user_id": user.id,
        "api_key_id": api_key.id,
        "raw_key": raw_key,
    }


@pytest_asyncio.fixture()
async def client(test_user_and_key):
    """Return an AsyncClient backed by a fresh per-test DB session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture()
def auth_headers(test_user_and_key):
    """Return Authorization headers for the test API key."""
    return {"Authorization": f"Bearer {test_user_and_key['raw_key']}"}
