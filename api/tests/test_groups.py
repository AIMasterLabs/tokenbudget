# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for user groups with project-level permissions and bulk user management."""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.group import Group, GroupMember, GroupProjectAccess
from app.models.project_member import ProjectMember
from app.services.auth_service import hash_password
from app.services.key_service import create_api_key

TEST_DATABASE_URL = "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget_test"


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def admin_user(db):
    """Create an admin user with an API key."""
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"admin_{unique}@tokenbudget.dev",
        name="Admin User",
        role="admin",
        password_hash=hash_password("adminpass"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    api_key, raw_key = await create_api_key(db, user.id, "Admin Key")
    return {"user": user, "raw_key": raw_key}


@pytest_asyncio.fixture()
async def member_user(db):
    """Create a regular member user with an API key."""
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"member_{unique}@tokenbudget.dev",
        name="Member User",
        role="member",
        password_hash=hash_password("memberpass"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    api_key, raw_key = await create_api_key(db, user.id, "Member Key")
    return {"user": user, "raw_key": raw_key}


@pytest_asyncio.fixture()
async def viewer_user(db):
    """Create a viewer user with an API key."""
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"viewer_{unique}@tokenbudget.dev",
        name="Viewer User",
        role="viewer",
        password_hash=hash_password("viewerpass"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    api_key, raw_key = await create_api_key(db, user.id, "Viewer Key")
    return {"user": user, "raw_key": raw_key}


@pytest_asyncio.fixture()
async def test_project(db, admin_user):
    """Create a test project owned by the admin."""
    project = Project(
        user_id=admin_user["user"].id,
        name="Test Project",
        slug=f"test-project-{uuid.uuid4().hex[:8]}",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@pytest_asyncio.fixture()
async def admin_client(admin_user):
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {admin_user['raw_key']}"
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture()
async def member_client(member_user):
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {member_user['raw_key']}"
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


# ── Group CRUD Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_group(admin_client):
    resp = await admin_client.post("/api/groups", json={"name": "Engineering", "description": "Engineering team"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Engineering"
    assert data["description"] == "Engineering team"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_group_duplicate(admin_client):
    name = f"DupGroup-{uuid.uuid4().hex[:8]}"
    resp1 = await admin_client.post("/api/groups", json={"name": name})
    assert resp1.status_code == 201
    resp2 = await admin_client.post("/api/groups", json={"name": name})
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_list_groups(admin_client):
    name = f"ListGroup-{uuid.uuid4().hex[:8]}"
    await admin_client.post("/api/groups", json={"name": name})
    resp = await admin_client.get("/api/groups")
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()]
    assert name in names


@pytest.mark.asyncio
async def test_get_group_detail(admin_client):
    resp = await admin_client.post("/api/groups", json={"name": f"Detail-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.get(f"/api/groups/{group_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "members" in data
    assert "project_access" in data


@pytest.mark.asyncio
async def test_update_group(admin_client):
    resp = await admin_client.post("/api/groups", json={"name": f"Update-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.put(f"/api/groups/{group_id}", json={"description": "Updated desc"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_delete_group_deactivates(admin_client):
    resp = await admin_client.post("/api/groups", json={"name": f"Delete-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.delete(f"/api/groups/{group_id}")
    assert resp.status_code == 200
    assert resp.json()["deactivated"] is True


@pytest.mark.asyncio
async def test_non_admin_cannot_create_group(member_client):
    resp = await member_client.post("/api/groups", json={"name": "Forbidden"})
    assert resp.status_code == 403


# ── Group Membership Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_user_to_group(admin_client, member_user):
    resp = await admin_client.post("/api/groups", json={"name": f"AddMember-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": str(member_user["user"].id)},
    )
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_add_user_to_group_duplicate(admin_client, member_user):
    resp = await admin_client.post("/api/groups", json={"name": f"DupMember-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    user_id = str(member_user["user"].id)
    await admin_client.post(f"/api/groups/{group_id}/members", json={"user_id": user_id})
    resp = await admin_client.post(f"/api/groups/{group_id}/members", json={"user_id": user_id})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_bulk_add_users_to_group(admin_client, member_user, admin_user):
    resp = await admin_client.post("/api/groups", json={"name": f"BulkAdd-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/groups/{group_id}/members/bulk",
        json={"user_ids": [str(member_user["user"].id), str(admin_user["user"].id)]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["added"] == 2
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_remove_user_from_group(admin_client, member_user):
    resp = await admin_client.post("/api/groups", json={"name": f"RemoveMember-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    user_id = str(member_user["user"].id)
    await admin_client.post(f"/api/groups/{group_id}/members", json={"user_id": user_id})
    resp = await admin_client.delete(f"/api/groups/{group_id}/members/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ── Group Project Access Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_group_to_project(admin_client, test_project):
    resp = await admin_client.post("/api/groups", json={"name": f"Assign-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": ["view_analytics", "view_costs"]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ok"] is True
    assert set(data["permissions"]) == {"view_analytics", "view_costs"}


@pytest.mark.asyncio
async def test_update_group_project_permissions(admin_client, test_project):
    resp = await admin_client.post("/api/groups", json={"name": f"UpdatePerm-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": ["view_analytics"]},
    )
    resp = await admin_client.put(
        f"/api/groups/{group_id}/projects/{test_project.id}",
        json={"permissions": ["view_analytics", "export_reports"]},
    )
    assert resp.status_code == 200
    assert "export_reports" in resp.json()["permissions"]


@pytest.mark.asyncio
async def test_revoke_group_project_access(admin_client, test_project):
    resp = await admin_client.post("/api/groups", json={"name": f"Revoke-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": ["view_analytics"]},
    )
    resp = await admin_client.delete(f"/api/groups/{group_id}/projects/{test_project.id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ── Group-Based Project Access Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_in_group_can_access_project(admin_client, member_client, member_user, test_project):
    """User in a group with project access should be able to see the project."""
    # Create group and assign member
    resp = await admin_client.post("/api/groups", json={"name": f"Access-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    await admin_client.post(
        f"/api/groups/{group_id}/members",
        json={"user_id": str(member_user["user"].id)},
    )
    # Assign group to project
    await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": ["view_analytics"]},
    )
    # Member should be able to access the project
    resp = await member_client.get(f"/api/projects/{test_project.id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_not_in_group_cannot_access_project(member_client, test_project):
    """User NOT in any group with project access and not a direct member should be denied."""
    resp = await member_client.get(f"/api/projects/{test_project.id}")
    assert resp.status_code == 403


# ── Permission-Level Checks ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_permissions_rejected(admin_client, test_project):
    """Assigning invalid permission names should be rejected."""
    resp = await admin_client.post("/api/groups", json={"name": f"Invalid-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": ["invalid_perm"]},
    )
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_empty_permissions_rejected(admin_client, test_project):
    """Empty permissions list should be rejected."""
    resp = await admin_client.post("/api/groups", json={"name": f"Empty-{uuid.uuid4().hex[:8]}"})
    group_id = resp.json()["id"]
    resp = await admin_client.post(
        f"/api/groups/{group_id}/projects",
        json={"project_id": str(test_project.id), "permissions": []},
    )
    assert resp.status_code == 422


# ── Bulk User Creation Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_create_users(admin_client):
    """Bulk create users with group assignment."""
    group_name = f"BulkGroup-{uuid.uuid4().hex[:8]}"
    await admin_client.post("/api/groups", json={"name": group_name})

    unique = uuid.uuid4().hex[:8]
    resp = await admin_client.post(
        "/api/admin/users/bulk",
        json={
            "users": [
                {
                    "email": f"alice_{unique}@co.com",
                    "password": "pass123",
                    "name": "Alice",
                    "role": "member",
                    "groups": [group_name],
                },
                {
                    "email": f"bob_{unique}@co.com",
                    "password": "pass456",
                    "name": "Bob",
                    "role": "viewer",
                    "groups": [group_name],
                },
            ]
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 2
    assert data["errors"] == 0
    assert all(r["ok"] for r in data["results"])


@pytest.mark.asyncio
async def test_bulk_create_users_duplicate_email(admin_client):
    """Bulk create with duplicate email should report error for that user."""
    unique = uuid.uuid4().hex[:8]
    email = f"dup_{unique}@co.com"

    # Create first
    await admin_client.post(
        "/api/admin/users/bulk",
        json={"users": [{"email": email, "password": "pass", "name": "First"}]},
    )

    # Try again — should get error
    resp = await admin_client.post(
        "/api/admin/users/bulk",
        json={"users": [{"email": email, "password": "pass", "name": "Dup"}]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["errors"] == 1
    assert data["results"][0]["ok"] is False


@pytest.mark.asyncio
async def test_non_admin_cannot_bulk_create(member_client):
    resp = await member_client.post(
        "/api/admin/users/bulk",
        json={"users": [{"email": "x@co.com", "password": "p", "name": "X"}]},
    )
    assert resp.status_code == 403
