# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.api_key import ApiKey
from app.models.event import Event
from app.schemas.analytics import AnalyticsSummary, TimeseriesPoint
from app.schemas.projects import ProjectCreate, ProjectUpdate


def _slugify(name: str) -> str:
    """Convert a project name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def _unique_slug(base_slug: str) -> str:
    """Append a short random suffix to make the slug unique."""
    suffix = uuid.uuid4().hex[:6]
    return f"{base_slug}-{suffix}"


async def _ensure_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """Return base_slug if available, else append random suffix until unique."""
    candidate = base_slug
    while True:
        q = select(Project).where(Project.slug == candidate)
        result = await db.execute(q)
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = _unique_slug(base_slug)


async def create_project(
    db: AsyncSession,
    user_id,
    data: ProjectCreate,
) -> Project:
    """Create a new project for a user, auto-generating a unique slug."""
    base_slug = _slugify(data.name)
    slug = await _ensure_unique_slug(db, base_slug)

    project = Project(
        user_id=user_id,
        name=data.name,
        slug=slug,
        description=data.description,
        color=data.color,
        is_active=True,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_projects(
    db: AsyncSession,
    user_id,
) -> list[Project]:
    """Return all projects owned by a user."""
    q = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_all_projects(
    db: AsyncSession,
) -> list[Project]:
    """Return all projects (for admins)."""
    q = select(Project).order_by(Project.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_accessible_projects(
    db: AsyncSession,
    user_id,
) -> list[Project]:
    """Return projects owned by user OR where user is a project member."""
    from sqlalchemy import or_

    q = (
        select(Project)
        .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            or_(
                Project.user_id == user_id,
                ProjectMember.user_id == user_id,
            )
        )
        .distinct()
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_project(
    db: AsyncSession,
    project_id,
    user_id,
) -> Project | None:
    """Return a single project scoped to the given user."""
    q = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def update_project(
    db: AsyncSession,
    project_id,
    user_id,
    data: ProjectUpdate,
) -> Project | None:
    """Update mutable fields on a project."""
    project = await get_project(db, project_id, user_id)
    if project is None:
        return None

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.color is not None:
        project.color = data.color
    if data.is_active is not None:
        project.is_active = data.is_active

    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(
    db: AsyncSession,
    project_id,
    user_id,
) -> bool:
    """Delete a project. Returns True if deleted, False if not found."""
    project = await get_project(db, project_id, user_id)
    if project is None:
        return False
    await db.delete(project)
    await db.commit()
    return True


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def get_project_analytics(
    db: AsyncSession,
    project_id,
    days: int = 30,
) -> AnalyticsSummary:
    """Return aggregate analytics for events belonging to a project."""
    since = _since(days)

    q = select(
        func.coalesce(func.sum(Event.cost_usd), 0).label("total_cost_usd"),
        func.count(Event.id).label("total_requests"),
        func.coalesce(func.sum(Event.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(Event.output_tokens), 0).label("total_output_tokens"),
        func.coalesce(func.avg(Event.cost_usd), 0).label("avg_cost_per_request"),
        func.coalesce(func.avg(Event.latency_ms), 0).label("avg_latency_ms"),
    ).where(Event.project_id == project_id, Event.created_at >= since)

    result = await db.execute(q)
    row = result.one()

    return AnalyticsSummary(
        total_cost_usd=float(row.total_cost_usd),
        total_requests=int(row.total_requests),
        total_input_tokens=int(row.total_input_tokens),
        total_output_tokens=int(row.total_output_tokens),
        avg_cost_per_request=float(row.avg_cost_per_request),
        avg_latency_ms=float(row.avg_latency_ms),
    )


async def get_project_timeseries(
    db: AsyncSession,
    project_id,
    days: int = 30,
) -> list[TimeseriesPoint]:
    """Return daily cost/request timeseries for a project."""
    since = _since(days)

    bucket = func.date_trunc("day", Event.created_at).label("bucket")

    q = (
        select(
            bucket,
            func.sum(Event.cost_usd).label("cost_usd"),
            func.count(Event.id).label("request_count"),
        )
        .where(Event.project_id == project_id, Event.created_at >= since)
        .group_by(bucket)
        .order_by(bucket)
    )

    result = await db.execute(q)
    rows = result.all()

    return [
        TimeseriesPoint(
            timestamp=r.bucket,
            cost_usd=float(r.cost_usd),
            request_count=int(r.request_count),
        )
        for r in rows
    ]


async def get_project_keys(
    db: AsyncSession,
    project_id,
) -> list[ApiKey]:
    """Return all API keys associated with a project."""
    q = (
        select(ApiKey)
        .where(ApiKey.project_id == project_id)
        .order_by(ApiKey.created_at.desc())
    )
    result = await db.execute(q)
    return list(result.scalars().all())
