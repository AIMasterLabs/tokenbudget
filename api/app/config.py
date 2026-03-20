# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Environment ────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # ── Signup kill switch ─────────────────────────────────────────────────
    SIGNUPS_ENABLED: bool = True
    SIGNUPS_PAUSED_MESSAGE: str = "New signups are temporarily paused. Check back soon."

    # ── Default limits (free & open-source — generous for everyone) ─────
    FREE_EVENTS_PER_MONTH: int = 10_000_000
    FREE_KEYS_MAX: int = 100
    FREE_RETENTION_DAYS: int = 365
    FREE_PROJECTS_MAX: int = 100

    # ── Rate limiting ──────────────────────────────────────────────────────
    RATE_LIMIT_EVENTS_PER_SECOND: int = 100
    RATE_LIMIT_BURST: int = 200

    # ── Input validation limits ────────────────────────────────────────────
    MAX_BATCH_SIZE: int = 1_000
    MAX_TAG_KEYS: int = 20
    MAX_TAG_VALUE_LENGTH: int = 256
    MAX_KEY_NAME_LENGTH: int = 100

    # ── Event field validation limits ──────────────────────────────────────
    MAX_COST_USD: float = 100.0
    MAX_INPUT_TOKENS: int = 2_000_000
    MAX_OUTPUT_TOKENS: int = 2_000_000
    MAX_TOTAL_TOKENS: int = 4_000_000
    MAX_LATENCY_MS: int = 300_000
    MAX_MODEL_LEN: int = 100
    VALID_PROVIDERS: list[str] = [
        "openai", "anthropic", "google", "mistral", "cohere",
        "meta", "amazon", "azure", "groq", "together", "other",
    ]

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    # Alias used by some callers
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:  # noqa: N802
        return self.CORS_ORIGINS

    # ── Auth Mode ─────────────────────────────────────────────────────────
    # Controls how users authenticate to the dashboard.
    #   "local"  — email + password with JWT (default, no external services)
    #   "clerk"  — Clerk OAuth (Google, magic link) — set keys below
    #   "none"   — no auth, single-user mode (auto-provisions API key)
    AUTH_MODE: str = "local"

    # ── Clerk Auth (only used when AUTH_MODE=clerk) ───────────────────────
    CLERK_SECRET_KEY: str = ""        # sk_live_... or sk_test_...
    CLERK_PUBLISHABLE_KEY: str = ""   # pk_live_... or pk_test_...

    # ── Admin ──────────────────────────────────────────────────────────────
    ADMIN_KEY: str = ""

    # ── Purge job settings ─────────────────────────────────────────────────
    PURGE_ENABLED: bool = True
    PURGE_BATCH_SIZE: int = 5_000
    PURGE_CRON_HOUR: int = 3   # 3 AM UTC
    PURGE_CRON_MINUTE: int = 0

    # ── Redis ──────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # ── Backward-compat aliases (old lowercase names) ──────────────────────
    # These allow existing code that reads settings.database_url / settings.redis_url
    # to keep working without modification while we migrate.
    @property
    def database_url(self) -> str:  # noqa: D401
        return self.DATABASE_URL

    @property
    def redis_url(self) -> str:  # noqa: D401
        return self.REDIS_URL

    # ── Limits helper ────────────────────────────────────────────────────
    def get_tier_limits(self, tier: str = "free") -> dict[str, Any]:
        """Return the single set of generous limits (tier arg kept for compat)."""
        return {
            "events_per_month": self.FREE_EVENTS_PER_MONTH,
            "keys_max": self.FREE_KEYS_MAX,
            "retention_days": self.FREE_RETENTION_DAYS,
            "projects_max": self.FREE_PROJECTS_MAX,
        }


config = Config()

# ---------------------------------------------------------------------------
# Backward-compatible alias so that files using `from app.config import settings`
# continue to work without any changes.
# ---------------------------------------------------------------------------
settings = config
