# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import config
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.keys import KeyCreate, KeyResponse, KeyCreateResponse, KeyRotateResponse
from app.services.key_service import create_api_key
from app.middleware.api_key_auth import require_api_key
from app.middleware.clerk_auth import require_clerk_or_api_key
from app.lib.tier_check import check_key_quota

router = APIRouter(prefix="/api", tags=["keys"])


async def _get_or_create_test_user(db: AsyncSession) -> User:
    """For development only: get the first user or create a test user."""
    if config.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test user creation is only allowed in development mode",
        )
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email="test@tokenbudget.dev",
            name="Test User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.post("/setup", response_model=KeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def setup_first_key(
    key_data: KeyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Bootstrap endpoint for self-hosted deployments.
    Creates a default user + first API key without requiring auth.
    Used by the frontend's auto-provisioning on first visit.
    """
    if not config.SIGNUPS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "signups_paused", "message": config.SIGNUPS_PAUSED_MESSAGE},
        )

    # Find or create the default local user
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email="admin@localhost", name="Admin")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Check quota before creating
    await check_key_quota(db, user.id, tier="free")

    api_key, raw_key = await create_api_key(db, user.id, key_data.name or "default")
    return KeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.post("/keys", response_model=KeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    key_data: KeyCreate,
    auth: tuple = Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. Requires authentication."""
    # Signup kill switch
    if not config.SIGNUPS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "signups_paused",
                "message": config.SIGNUPS_PAUSED_MESSAGE,
            },
        )

    _, user = auth

    # Enforce per-user key quota (use "free" tier for all users for now)
    await check_key_quota(db, user.id, tier="free")

    api_key, raw_key = await create_api_key(db, user.id, key_data.name)
    return KeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.get("/keys", response_model=list[KeyResponse])
async def list_keys(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """List all active API keys for the authenticated user."""
    _, user = auth
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True)
    )
    keys = result.scalars().all()
    return keys


@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an API key."""
    _, user = auth
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    api_key.is_active = False
    await db.commit()


@router.post("/keys/{key_id}/rotate", response_model=KeyRotateResponse, status_code=status.HTTP_201_CREATED)
async def rotate_key(
    key_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Rotate an API key: create a new key with the same name/project, revoke the old one."""
    _, user = auth

    # Find the old key, must belong to this user
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    old_key = result.scalar_one_or_none()
    if old_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    if not old_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key is already inactive",
        )

    # Create a new key with the same name and project
    new_key, raw_key = await create_api_key(
        db, user.id, old_key.name, team_id=old_key.team_id
    )

    # Optionally carry over project_id
    if old_key.project_id is not None:
        new_key.project_id = old_key.project_id

    # Revoke the old key
    old_key.is_active = False

    await db.commit()
    await db.refresh(new_key)

    return KeyRotateResponse(
        id=new_key.id,
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        is_active=new_key.is_active,
        created_at=new_key.created_at,
        raw_key=raw_key,
        rotated_key_id=old_key.id,
    )
