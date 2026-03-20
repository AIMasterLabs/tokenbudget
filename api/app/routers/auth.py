# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Authentication router — register, login, me, change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.clerk_auth import require_clerk_or_api_key
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserInfo,
)
from app.services.auth_service import (
    authenticate_user,
    create_jwt_token,
    hash_password,
    register_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        department=user.department,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user. First user ever becomes admin automatically."""
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await register_user(db, email=data.email, password=data.password, name=data.name)
    token = create_jwt_token(str(user.id), user.role)
    return AuthResponse(token=token, user=_user_info(user))


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password, receive JWT."""
    user = await authenticate_user(db, email=data.email, password=data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_jwt_token(str(user.id), user.role)
    return AuthResponse(token=token, user=_user_info(user))


@router.get("/me", response_model=UserInfo)
async def get_me(
    auth=Depends(require_clerk_or_api_key),
):
    """Return current user info (requires JWT or API key)."""
    _, user = auth
    return _user_info(user)


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    auth=Depends(require_clerk_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password (requires JWT or API key)."""
    _, user = auth
    if user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a local password set",
        )
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"ok": True}
