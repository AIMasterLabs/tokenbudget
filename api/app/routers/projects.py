# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.middleware.clerk_auth import require_clerk_or_api_key
from app.middleware.permissions import require_role
from app.models.api_key import ApiKey
from app.models.group import GroupMember, GroupProjectAccess
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.analytics import AnalyticsSummary, TimeseriesPoint
from app.schemas.keys import KeyResponse
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        description=project.description,
        color=project.color,
        is_active=project.is_active,
        created_at=project.created_at,
    )


async def _get_accessible_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: User,
):
    """Return a project if the user has access, else raise 404/403."""
    from app.models.project import Project

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Admins see everything
    if user.role == "admin":
        return project

    # Owner always has access
    if project.user_id == user.id:
        return project

    # Check project_members table
    mem_result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if mem_result.scalar_one_or_none() is not None:
        return project

    # Check group-based project access
    group_result = await db.execute(
        select(GroupProjectAccess)
        .join(GroupMember, GroupMember.group_id == GroupProjectAccess.group_id)
        .where(
            GroupMember.user_id == user.id,
            GroupProjectAccess.project_id == project_id,
        )
    )
    if group_result.first() is not None:
        return project

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this project")


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    # Viewers cannot create projects
    if user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot create projects",
        )
    project = await project_service.create_project(db, user_id=user.id, data=data)

    # Auto-add creator as project member
    pm = ProjectMember(user_id=user.id, project_id=project.id, role="admin")
    db.add(pm)
    await db.commit()

    return _to_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    if user.role == "admin":
        # Admins see all projects
        projects = await project_service.get_all_projects(db)
    else:
        # Members/viewers see owned projects + assigned projects
        projects = await project_service.get_accessible_projects(db, user_id=user.id)
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    project = await _get_accessible_project(db, project_id, user)
    return _to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    if user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify projects",
        )
    project = await _get_accessible_project(db, project_id, user)
    project = await project_service.update_project(
        db, project_id=project_id, user_id=project.user_id, data=data
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return _to_response(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    if user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot delete projects",
        )
    project = await _get_accessible_project(db, project_id, user)
    deleted = await project_service.delete_project(db, project_id=project_id, user_id=project.user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return {"deleted": True}


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "member",
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to a project (admin only)."""
    _, admin_user = auth
    from app.models.project import Project

    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Verify target user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if already a member
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a project member")

    if role not in ("admin", "member", "viewer"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    pm = ProjectMember(user_id=user_id, project_id=project_id, role=role)
    db.add(pm)
    await db.commit()
    return {"ok": True, "user_id": str(user_id), "project_id": str(project_id), "role": role}


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    auth=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user from a project (admin only)."""
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    pm = result.scalar_one_or_none()
    if pm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    await db.delete(pm)
    await db.commit()
    return {"deleted": True}


@router.get("/{project_id}/analytics/summary", response_model=AnalyticsSummary)
async def get_project_analytics_summary(
    project_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    await _get_accessible_project(db, project_id, user)
    return await project_service.get_project_analytics(db, project_id=project_id, days=days)


@router.get("/{project_id}/analytics/timeseries", response_model=list[TimeseriesPoint])
async def get_project_analytics_timeseries(
    project_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    await _get_accessible_project(db, project_id, user)
    return await project_service.get_project_timeseries(db, project_id=project_id, days=days)


@router.get("/{project_id}/keys", response_model=list[KeyResponse])
async def get_project_keys(
    project_id: uuid.UUID,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    await _get_accessible_project(db, project_id, user)
    keys = await project_service.get_project_keys(db, project_id=project_id)
    return [
        KeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            created_at=k.created_at,
        )
        for k in keys
    ]
