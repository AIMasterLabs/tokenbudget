# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Clerk JWT verification for dashboard routes.
Falls back gracefully when CLERK_SECRET_KEY is not configured.

Two auth systems coexist:
- Clerk JWT: for dashboard UI (web browser users)
- API Key (tb_ak_): for SDK and proxy (programmatic access)
"""
from __future__ import annotations

import logging
import time

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

# Cache for Clerk JWKS keys — avoids fetching on every request.
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS: float = 3600.0  # 1 hour


async def _get_clerk_jwks() -> dict:
    """Fetch Clerk's JWKS key set (cached with 1-hour TTL)."""
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache is not None and (time.monotonic() - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    # Clerk publishes JWKS at a well-known endpoint derived from the secret key.
    # The frontend publishable key contains the instance identifier.
    # We use the standard Clerk JWKS endpoint.
    clerk_issuer = None
    if config.CLERK_PUBLISHABLE_KEY:
        # pk_test_xxxx or pk_live_xxxx — extract instance id
        parts = config.CLERK_PUBLISHABLE_KEY.split("_")
        if len(parts) >= 3:
            import base64
            # Clerk publishable key encodes the Frontend API URL
            encoded = parts[2]
            # Add padding
            encoded += "=" * (4 - len(encoded) % 4) if len(encoded) % 4 else ""
            try:
                clerk_issuer = base64.b64decode(encoded).decode("utf-8")
            except Exception:
                pass

    if not clerk_issuer:
        # Fallback: use Clerk's API to get JWKS
        jwks_url = "https://api.clerk.com/v1/jwks"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                jwks_url,
                headers={"Authorization": f"Bearer {config.CLERK_SECRET_KEY}"},
            )
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_fetched_at = time.monotonic()
            return _jwks_cache

    jwks_url = f"https://{clerk_issuer}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.monotonic()
        return _jwks_cache


def _clerk_is_configured() -> bool:
    """Return True if Clerk keys are set to real values."""
    return bool(
        config.CLERK_SECRET_KEY
        and config.CLERK_SECRET_KEY not in ("", "sk_test_REPLACE_ME")
    )


async def _verify_clerk_jwt(token: str) -> dict:
    """Verify a Clerk JWT and return its payload."""
    jwks_data = await _get_clerk_jwks()

    # Get the signing key from JWKS
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    signing_key = None
    for key in jwks_data.get("keys", []):
        if key.get("kid") == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break

    if signing_key is None:
        # Invalidate cache and retry once (key rotation)
        global _jwks_cache
        _jwks_cache = None
        jwks_data = await _get_clerk_jwks()
        for key in jwks_data.get("keys", []):
            if key.get("kid") == kid:
                signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break

    if signing_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find matching Clerk signing key",
        )

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk session has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Clerk token: {e}",
        )

    return payload


async def require_clerk_or_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts EITHER:
    1. Bearer tb_ak_ API key (for programmatic access / SDK)
    2. Local JWT (signed with SECRET_KEY, issuer=tokenbudget)
    3. Clerk session JWT (for dashboard UI, requires CLERK_SECRET_KEY)

    Returns (ApiKey, User) when authenticated via API key,
    or (None, User) when authenticated via local JWT or Clerk JWT.
    """

    # ── Path 1: API key (always active) ────────────────────────────────────
    if credentials is not None and credentials.credentials.startswith("tb_ak_"):
        from app.middleware.api_key_auth import require_api_key

        return await require_api_key(credentials=credentials, db=db)

    # ── Path 2: Local JWT (try to decode with our SECRET_KEY) ──────────────
    if credentials is not None:
        token = credentials.credentials
        try:
            from app.services.auth_service import decode_jwt_token
            payload = decode_jwt_token(token)
            user_id = payload.get("sub")
            if user_id:
                import uuid
                result = await db.execute(
                    select(User).where(User.id == uuid.UUID(user_id))
                )
                user = result.scalar_one_or_none()
                if user is not None and user.is_active:
                    return (None, user)
        except (jwt.InvalidTokenError, ValueError, Exception):
            # Not a valid local JWT — fall through to Clerk
            pass

    # ── Path 3: Clerk JWT (active when CLERK_SECRET_KEY is configured) ─────
    if credentials is not None and _clerk_is_configured():
        token = credentials.credentials
        payload = await _verify_clerk_jwt(token)

        clerk_user_id = payload.get("sub")  # e.g. "user_2abc..."
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clerk token missing subject claim",
            )

        # Find or auto-provision the local User record.
        result = await db.execute(
            select(User).where(User.clerk_id == clerk_user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Extract email from Clerk token metadata if available.
            email = (
                payload.get("email")
                or payload.get("email_address")
                or f"{clerk_user_id}@clerk.tokenbudget.com"
            )
            name = payload.get("name") or payload.get("first_name") or ""
            user = User(clerk_id=clerk_user_id, email=email, name=name)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Return (None, user) to match the (ApiKey, User) shape.
        return (None, user)

    # ── Fallback: neither auth method succeeded ─────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer tb_ak_ API key, JWT token, or Clerk session token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
