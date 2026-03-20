# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import hashlib
import secrets
import uuid

import bcrypt
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import config
from app.models.api_key import ApiKey


# ---------------------------------------------------------------------------
# Low-level key helpers
# ---------------------------------------------------------------------------

def generate_key() -> tuple[str, str, str]:
    """Generate a raw API key and return (raw_key, bcrypt_hash, sha256_hex)."""
    raw_key = "tb_ak_" + secrets.token_hex(16)
    hashed = hash_key(raw_key)
    digest = sha256_key(raw_key)
    return raw_key, hashed, digest


def hash_key(raw_key: str) -> str:
    """Bcrypt hash an API key."""
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_key(raw_key: str, hashed: str) -> bool:
    """Verify a raw key against its bcrypt hash."""
    return bcrypt.checkpw(raw_key.encode(), hashed.encode())


def sha256_key(raw_key: str) -> str:
    """Return the hex SHA-256 digest of a raw key (used for fast DB lookup)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Redis helpers  (fail-open: any Redis error is silently swallowed)
# ---------------------------------------------------------------------------

async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(config.REDIS_URL, decode_responses=False)


async def _redis_get(key: str) -> str | None:
    try:
        r = await _get_redis()
        val = await r.get(key)
        await r.aclose()
        return val.decode() if val else None
    except Exception:
        return None


async def _redis_set(key: str, value: str, ex: int = 300) -> None:
    try:
        r = await _get_redis()
        await r.set(key, value, ex=ex)
        await r.aclose()
    except Exception:
        pass


async def _redis_delete(key: str) -> None:
    try:
        r = await _get_redis()
        await r.delete(key)
        await r.aclose()
    except Exception:
        pass


async def invalidate_key_cache(raw_key: str) -> None:
    """Remove the Redis cache entry for a given raw API key."""
    digest = sha256_key(raw_key)
    await _redis_delete(f"apikey:{digest}")


# ---------------------------------------------------------------------------
# DB service functions
# ---------------------------------------------------------------------------

async def create_api_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    team_id: uuid.UUID | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key in the database. Returns (ApiKey model, raw_key)."""
    raw_key, key_hash, key_sha256 = generate_key()
    key_prefix = raw_key[:8]  # first 8 chars: "tb_ak_ab"

    api_key = ApiKey(
        user_id=user_id,
        team_id=team_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        key_sha256=key_sha256,
        name=name,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key


async def get_api_key_by_raw(db: AsyncSession, raw_key: str) -> ApiKey | None:
    """
    Find an active API key — O(1) via SHA-256 indexed column + Redis cache.

    Falls back to the legacy O(N) bcrypt scan for keys that pre-date the
    sha256 column (key_sha256 IS NULL), so old keys continue to work until
    they are rotated.
    """
    digest = sha256_key(raw_key)
    cache_key = f"apikey:{digest}"

    # 1. Redis cache hit — fetch the full row by id
    cached_id = await _redis_get(cache_key)
    if cached_id:
        result = await db.execute(
            select(ApiKey).where(ApiKey.id == uuid.UUID(cached_id))
        )
        key = result.scalar_one_or_none()
        if key and key.is_active:
            return key
        # Stale cache (key deactivated) — fall through to DB
        await _redis_delete(cache_key)

    # 2. O(1) DB lookup via indexed SHA-256 column
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_sha256 == digest,
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()

    if key:
        await _redis_set(cache_key, str(key.id), ex=300)
        return key

    # 3. Legacy fallback: bcrypt scan for keys without sha256 populated
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_sha256 == None,  # noqa: E711
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    legacy_keys = result.scalars().all()
    for legacy_key in legacy_keys:
        if verify_key(raw_key, legacy_key.key_hash):
            # Backfill sha256 so future lookups are fast
            legacy_key.key_sha256 = digest
            await db.commit()
            await _redis_set(cache_key, str(legacy_key.id), ex=300)
            return legacy_key

    return None
