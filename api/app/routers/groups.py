# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Groups router — CRUD, membership, project access, bulk user creation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.clerk_auth import require_clerk_or_api_key
from app.middleware.permissions import require_role
from app.models.group import Group, GroupMember, GroupProjectAccess
from app.models.project import Project
from app.models.user import User
from app.schemas.groups import (
    BulkUserCreate,
    BulkUserCreateResponse,
    BulkUserResultEntry,
    GroupCreate,
    GroupDetail,
    GroupMemberAdd,
    GroupMemberBulkAdd,
    GroupMemberResponse,
    GroupProjectAccessCreate,
    GroupProjectAccessResponse,
    GroupProjectAccessUpdate,
    GroupResponse,
    GroupUpdate,
)
from app.services.auth_service import hash_password

router = APIRouter(tags=["groups"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _group_response(g: Group) -> GroupResponse:
    return GroupResponse(
        id=str(g.id),
        name=g.name,
        description=g.description,
        is_active=g.is_active,
        created_at=g.created_at,
    )


async def _get_active_group(db: AsyncSession, group_id: uuid.UUID) -> Group:
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


# ── Group CRUD ───────────────────────────────────────────────────────────────

@router.post("/api/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new group (admin only)."""
    # Check uniqueness
    existing = await db.execute(select(Group).where(Group.name == data.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group name already exists")

    group = Group(name=data.name, description=data.description)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return _group_response(group)


@router.get("/api/groups", response_model=list[GroupResponse])
async def list_groups(
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all groups (admin only)."""
    result = await db.execute(select(Group).order_by(Group.name))
    groups = result.scalars().all()
    return [_group_response(g) for g in groups]


@router.get("/api/groups/{group_id}", response_model=GroupDetail)
async def get_group(
    group_id: uuid.UUID,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get group detail with members and project access."""
    group = await _get_active_group(db, group_id)

    # Fetch members with user info
    members_result = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
    )
    members = [
        GroupMemberResponse(
            id=str(gm.id),
            user_id=str(gm.user_id),
            email=u.email,
            name=u.name,
            added_at=gm.added_at,
        )
        for gm, u in members_result.all()
    ]

    # Fetch project access with project names
    access_result = await db.execute(
        select(GroupProjectAccess, Project)
        .join(Project, GroupProjectAccess.project_id == Project.id)
        .where(GroupProjectAccess.group_id == group_id)
    )
    project_access = [
        GroupProjectAccessResponse(
            id=str(gpa.id),
            project_id=str(gpa.project_id),
            project_name=p.name,
            permissions=gpa.permissions,
            granted_at=gpa.granted_at,
        )
        for gpa, p in access_result.all()
    ]

    return GroupDetail(
        id=str(group.id),
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        created_at=group.created_at,
        members=members,
        project_access=project_access,
    )


@router.put("/api/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    data: GroupUpdate,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update group name/description (admin only)."""
    group = await _get_active_group(db, group_id)
    if data.name is not None:
        # Check uniqueness if changing name
        existing = await db.execute(
            select(Group).where(Group.name == data.name, Group.id != group_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group name already exists")
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    await db.commit()
    await db.refresh(group)
    return _group_response(group)


@router.delete("/api/groups/{group_id}")
async def delete_group(
    group_id: uuid.UUID,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a group (admin only)."""
    group = await _get_active_group(db, group_id)
    group.is_active = False
    await db.commit()
    return {"ok": True, "deactivated": True}


# ── Group Membership ─────────────────────────────────────────────────────────

@router.post("/api/groups/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_group_member(
    group_id: uuid.UUID,
    data: GroupMemberAdd,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Add a single user to a group."""
    group = await _get_active_group(db, group_id)
    user_id = uuid.UUID(data.user_id)

    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if already a member
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a group member")

    gm = GroupMember(group_id=group_id, user_id=user_id)
    db.add(gm)
    await db.commit()
    return {"ok": True, "group_id": str(group_id), "user_id": str(user_id)}


@router.post("/api/groups/{group_id}/members/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_add_group_members(
    group_id: uuid.UUID,
    data: GroupMemberBulkAdd,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Add multiple users to a group."""
    group = await _get_active_group(db, group_id)
    added = []
    errors = []

    for uid_str in data.user_ids:
        try:
            user_id = uuid.UUID(uid_str)
        except ValueError:
            errors.append({"user_id": uid_str, "error": "Invalid UUID"})
            continue

        # Verify user exists
        result = await db.execute(select(User).where(User.id == user_id))
        if result.scalar_one_or_none() is None:
            errors.append({"user_id": uid_str, "error": "User not found"})
            continue

        # Check if already a member
        result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            errors.append({"user_id": uid_str, "error": "Already a member"})
            continue

        gm = GroupMember(group_id=group_id, user_id=user_id)
        db.add(gm)
        added.append(uid_str)

    await db.commit()
    return {"added": len(added), "errors": errors, "added_user_ids": added}


@router.delete("/api/groups/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from a group."""
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    gm = result.scalar_one_or_none()
    if gm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    await db.delete(gm)
    await db.commit()
    return {"deleted": True}


# ── Group Project Access ─────────────────────────────────────────────────────

@router.post("/api/groups/{group_id}/projects", status_code=status.HTTP_201_CREATED)
async def assign_group_to_project(
    group_id: uuid.UUID,
    data: GroupProjectAccessCreate,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Assign a group to a project with specific permissions."""
    group = await _get_active_group(db, group_id)
    project_id = uuid.UUID(data.project_id)

    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check if already assigned
    result = await db.execute(
        select(GroupProjectAccess).where(
            GroupProjectAccess.group_id == group_id,
            GroupProjectAccess.project_id == project_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Group already assigned to this project")

    gpa = GroupProjectAccess(
        group_id=group_id,
        project_id=project_id,
        permissions=data.permissions,
    )
    db.add(gpa)
    await db.commit()
    await db.refresh(gpa)
    return {
        "ok": True,
        "id": str(gpa.id),
        "group_id": str(group_id),
        "project_id": str(project_id),
        "permissions": gpa.permissions,
    }


@router.put("/api/groups/{group_id}/projects/{project_id}")
async def update_group_project_access(
    group_id: uuid.UUID,
    project_id: uuid.UUID,
    data: GroupProjectAccessUpdate,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update permissions for a group-project assignment."""
    result = await db.execute(
        select(GroupProjectAccess).where(
            GroupProjectAccess.group_id == group_id,
            GroupProjectAccess.project_id == project_id,
        )
    )
    gpa = result.scalar_one_or_none()
    if gpa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group-project access not found")

    gpa.permissions = data.permissions
    await db.commit()
    return {"ok": True, "permissions": gpa.permissions}


@router.delete("/api/groups/{group_id}/projects/{project_id}")
async def revoke_group_project_access(
    group_id: uuid.UUID,
    project_id: uuid.UUID,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a group's access to a project."""
    result = await db.execute(
        select(GroupProjectAccess).where(
            GroupProjectAccess.group_id == group_id,
            GroupProjectAccess.project_id == project_id,
        )
    )
    gpa = result.scalar_one_or_none()
    if gpa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group-project access not found")
    await db.delete(gpa)
    await db.commit()
    return {"deleted": True}


# ── Bulk User Creation ───────────────────────────────────────────────────────

@router.post("/api/admin/users/bulk", response_model=BulkUserCreateResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_users(
    data: BulkUserCreate,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create users with optional group assignments (admin only)."""
    results = []
    created_count = 0
    error_count = 0

    for entry in data.users:
        try:
            # Check if email already exists
            existing = await db.execute(select(User).where(User.email == entry.email))
            if existing.scalar_one_or_none() is not None:
                results.append(BulkUserResultEntry(email=entry.email, ok=False, error="Email already exists"))
                error_count += 1
                continue

            # Create user
            user = User(
                email=entry.email,
                name=entry.name,
                password_hash=hash_password(entry.password),
                role=entry.role,
                department=entry.department,
                is_active=True,
            )
            db.add(user)
            await db.flush()  # get the user.id

            # Assign to groups by name
            for group_name in entry.groups:
                group_result = await db.execute(
                    select(Group).where(Group.name == group_name, Group.is_active == True)
                )
                group = group_result.scalar_one_or_none()
                if group is not None:
                    gm = GroupMember(group_id=group.id, user_id=user.id)
                    db.add(gm)

            results.append(BulkUserResultEntry(email=entry.email, id=str(user.id), ok=True))
            created_count += 1

        except Exception as e:
            results.append(BulkUserResultEntry(email=entry.email, ok=False, error=str(e)))
            error_count += 1

    await db.commit()
    return BulkUserCreateResponse(created=created_count, errors=error_count, results=results)
