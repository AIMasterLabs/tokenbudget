# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for local JWT auth with roles and project-level access control."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db
from app.models.base import Base

TEST_DATABASE_URL = "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"


@pytest_asyncio.fixture()
async def auth_client():
    """
    Return an AsyncClient with a fresh DB (tables recreated).
    No pre-existing users so first register becomes admin.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Recreate tables for a clean slate
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_first_user_becomes_admin(auth_client):
    """First user ever registered should automatically become admin."""
    resp = await auth_client.post("/api/auth/register", json={
        "email": "admin@test.com",
        "password": "StrongPass123!",
        "name": "Admin User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_register_second_user_becomes_member(auth_client):
    """Second user should default to member role."""
    # First user -> admin
    await auth_client.post("/api/auth/register", json={
        "email": "admin@test.com",
        "password": "StrongPass123!",
        "name": "Admin",
    })
    # Second user -> member
    resp = await auth_client.post("/api/auth/register", json={
        "email": "member@test.com",
        "password": "StrongPass123!",
        "name": "Member",
    })
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "member"


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client):
    """Registering with an existing email should return 409."""
    await auth_client.post("/api/auth/register", json={
        "email": "dup@test.com",
        "password": "StrongPass123!",
        "name": "User",
    })
    resp = await auth_client.post("/api/auth/register", json={
        "email": "dup@test.com",
        "password": "Other456!",
        "name": "User2",
    })
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_correct_password(auth_client):
    """Login with correct password returns JWT."""
    await auth_client.post("/api/auth/register", json={
        "email": "login@test.com",
        "password": "MyPassword1!",
        "name": "Login User",
    })
    resp = await auth_client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "MyPassword1!",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client):
    """Login with wrong password returns 401."""
    await auth_client.post("/api/auth/register", json={
        "email": "wrong@test.com",
        "password": "Correct1!",
        "name": "User",
    })
    resp = await auth_client.post("/api/auth/login", json={
        "email": "wrong@test.com",
        "password": "Incorrect1!",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# JWT works for API calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jwt_works_for_me_endpoint(auth_client):
    """A valid JWT should authenticate /api/auth/me."""
    resp = await auth_client.post("/api/auth/register", json={
        "email": "me@test.com",
        "password": "StrongPass123!",
        "name": "Me User",
    })
    token = resp.json()["token"]
    me_resp = await auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "me@test.com"


# ---------------------------------------------------------------------------
# Project access control
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_sees_all_projects(auth_client):
    """Admin should see all projects, even those created by others."""
    # Register admin (first user)
    admin_resp = await auth_client.post("/api/auth/register", json={
        "email": "admin2@test.com",
        "password": "AdminPass1!",
        "name": "Admin",
    })
    admin_token = admin_resp.json()["token"]

    # Register member (second user)
    member_resp = await auth_client.post("/api/auth/register", json={
        "email": "member2@test.com",
        "password": "MemberPass1!",
        "name": "Member",
    })
    member_token = member_resp.json()["token"]

    # Member creates a project
    create_resp = await auth_client.post(
        "/api/projects",
        json={"name": "Member Project"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert create_resp.status_code == 201

    # Admin lists projects -> should see member's project
    list_resp = await auth_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert len(projects) >= 1
    assert any(p["name"] == "Member Project" for p in projects)


@pytest.mark.asyncio
async def test_member_sees_only_assigned_projects(auth_client):
    """Member should only see their own projects."""
    # Register admin
    admin_resp = await auth_client.post("/api/auth/register", json={
        "email": "admin3@test.com",
        "password": "AdminPass1!",
        "name": "Admin",
    })
    admin_token = admin_resp.json()["token"]

    # Register member
    member_resp = await auth_client.post("/api/auth/register", json={
        "email": "member3@test.com",
        "password": "MemberPass1!",
        "name": "Member",
    })
    member_token = member_resp.json()["token"]

    # Admin creates a project
    await auth_client.post(
        "/api/projects",
        json={"name": "Admin Only Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Member creates a project
    await auth_client.post(
        "/api/projects",
        json={"name": "Member Own Project"},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    # Member lists projects -> should NOT see admin's project
    list_resp = await auth_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert list_resp.status_code == 200
    projects = list_resp.json()
    names = [p["name"] for p in projects]
    assert "Member Own Project" in names
    assert "Admin Only Project" not in names


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(auth_client):
    """Viewer role should not be allowed to create projects."""
    # Register admin
    admin_resp = await auth_client.post("/api/auth/register", json={
        "email": "admin4@test.com",
        "password": "AdminPass1!",
        "name": "Admin",
    })
    admin_token = admin_resp.json()["token"]

    # Register a user (will be member)
    viewer_resp = await auth_client.post("/api/auth/register", json={
        "email": "viewer@test.com",
        "password": "ViewerPass1!",
        "name": "Viewer",
    })
    viewer_token = viewer_resp.json()["token"]
    viewer_id = viewer_resp.json()["user"]["id"]

    # Admin changes user role to viewer via DB (simulate)
    # We'll do this by calling the auth service directly via a helper endpoint
    # Instead, let's use the fact that we can update the user role through the DB
    # We need to update the user role to "viewer" — use a direct DB approach
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import update
    from app.models.user import User
    import uuid

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            update(User).where(User.id == uuid.UUID(viewer_id)).values(role="viewer")
        )
        await session.commit()
    await engine.dispose()

    # Viewer tries to create a project -> should fail
    create_resp = await auth_client.post(
        "/api/projects",
        json={"name": "Viewer Project"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert create_resp.status_code == 403


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_change_password(auth_client):
    """Changing password should work, and old password should stop working."""
    # Register
    resp = await auth_client.post("/api/auth/register", json={
        "email": "changepw@test.com",
        "password": "OldPass123!",
        "name": "PW User",
    })
    token = resp.json()["token"]

    # Change password
    change_resp = await auth_client.post(
        "/api/auth/change-password",
        json={"old_password": "OldPass123!", "new_password": "NewPass456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == 200

    # Login with new password works
    login_resp = await auth_client.post("/api/auth/login", json={
        "email": "changepw@test.com",
        "password": "NewPass456!",
    })
    assert login_resp.status_code == 200

    # Login with old password fails
    login_resp2 = await auth_client.post("/api/auth/login", json={
        "email": "changepw@test.com",
        "password": "OldPass123!",
    })
    assert login_resp2.status_code == 401
