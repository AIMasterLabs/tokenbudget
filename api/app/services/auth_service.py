# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Local JWT authentication service.

Handles password hashing, JWT creation/verification, and user registration/login.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.models.user import User

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_jwt_token(user_id: str, role: str) -> str:
    """Create a signed JWT token with 30-day expiry."""
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iss": "tokenbudget",
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(
        token,
        config.SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        issuer="tokenbudget",
    )


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
    role: str = "member",
) -> User:
    """Register a new user. First user ever becomes admin automatically."""
    # Check if this is the first user
    count_result = await db.execute(select(func.count(User.id)))
    user_count = count_result.scalar()

    if user_count == 0:
        role = "admin"

    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user by email and password. Returns None on failure."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if user.password_hash is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user
