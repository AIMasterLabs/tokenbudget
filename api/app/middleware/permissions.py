# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Role-based and project-level access control dependencies.

- require_role(*roles): checks that the user's global role is in the allowed set.
- require_project_access(project_id): checks the user is a member of the project,
  in a group with project access, OR is admin.
- require_project_permission(project_id, permission): checks group-level permission too.
"""
from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.clerk_auth import require_clerk_or_api_key
from app.models.project_member import ProjectMember
from app.models.group import GroupMember, GroupProjectAccess


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that checks the user's role is in *roles*."""

    async def _check(auth=Depends(require_clerk_or_api_key)):
        _, user = auth
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted. Required: {', '.join(roles)}",
            )
        return auth

    return _check


async def _get_group_project_access(
    db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID
) -> list[str] | None:
    """
    Return combined permissions if the user belongs to any group that has access
    to the given project, or None if no group access exists.
    """
    result = await db.execute(
        select(GroupProjectAccess.permissions)
        .join(GroupMember, GroupMember.group_id == GroupProjectAccess.group_id)
        .where(
            GroupMember.user_id == user_id,
            GroupProjectAccess.project_id == project_id,
        )
    )
    rows = result.all()
    if not rows:
        return None
    # Merge permissions from all matching groups
    merged: set[str] = set()
    for (perms,) in rows:
        if isinstance(perms, list):
            merged.update(perms)
    return list(merged)


async def require_project_access(
    project_id: uuid.UUID,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Check that the current user has access to the given project.

    - Admins bypass all project checks (they see everything).
    - Direct project_members membership grants access.
    - Group-based project access also grants access.
    """
    _, user = auth
    if user.role == "admin":
        return auth

    # Direct membership
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        return auth

    # Group-based access
    group_perms = await _get_group_project_access(db, user.id, project_id)
    if group_perms is not None:
        return auth

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this project",
    )


def require_project_permission(permission: str) -> Callable:
    """
    Return a FastAPI dependency that checks the user has a specific permission
    for a project — either via direct membership (all permissions) or via
    group-based access (only the permissions listed in GroupProjectAccess).
    """

    async def _check(
        project_id: uuid.UUID,
        auth=Depends(require_clerk_or_api_key),
        db: AsyncSession = Depends(get_db),
    ):
        _, user = auth
        if user.role == "admin":
            return auth

        # Direct membership grants all permissions
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return auth

        # Group-based: check specific permission
        group_perms = await _get_group_project_access(db, user.id, project_id)
        if group_perms is not None and permission in group_perms:
            return auth

        if group_perms is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have the '{permission}' permission for this project",
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    return _check
