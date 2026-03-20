# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.routers import health, events, keys, analytics, budgets, pricing, projects, waitlist, proxy, alerts, otlp, exports, price_changes, admin_pricing, auth, groups

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APScheduler instance
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler()


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup validation ──────────────────────────────────────────────
    if config.ENVIRONMENT == "production":
        if config.SECRET_KEY == "change-me-in-production":
            raise RuntimeError(
                "SECRET_KEY must be changed from the default value in production!"
            )
        if "*" in config.CORS_ORIGINS:
            raise RuntimeError(
                "CORS_ORIGINS must not contain '*' in production!"
            )

    if not config.ADMIN_KEY:
        logger.warning(
            "ADMIN_KEY is not set — admin endpoints are unprotected. "
            "Set ADMIN_KEY in your environment."
        )

    free_limits = config.get_tier_limits("free")
    logger.info(
        "Free tier limits: %d events/month, %d keys max, %d days retention, %d projects max",
        free_limits["events_per_month"],
        free_limits["keys_max"],
        free_limits["retention_days"],
        free_limits["projects_max"],
    )

    # ── APScheduler purge job ───────────────────────────────────────────
    if config.PURGE_ENABLED:
        from app.jobs.purge_old_events import run_purge

        scheduler.add_job(
            run_purge,
            trigger="cron",
            hour=config.PURGE_CRON_HOUR,
            minute=config.PURGE_CRON_MINUTE,
            id="nightly_purge",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Nightly purge job scheduled at %02d:%02d UTC (retention=%d days)",
            config.PURGE_CRON_HOUR,
            config.PURGE_CRON_MINUTE,
            config.FREE_RETENTION_DAYS,
        )
    else:
        logger.info("Nightly purge job is DISABLED (PURGE_ENABLED=false)")

    yield

    # ── Shutdown ────────────────────────────────────────────────────────
    if scheduler.running:
        scheduler.shutdown(wait=False)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="TokenBudget API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(events.router)
app.include_router(keys.router)
app.include_router(analytics.router)
app.include_router(budgets.router)
app.include_router(pricing.router)
app.include_router(projects.router)
app.include_router(waitlist.router)
app.include_router(proxy.router)
app.include_router(alerts.router)
app.include_router(otlp.router)
app.include_router(exports.router)
app.include_router(price_changes.router)
app.include_router(admin_pricing.router)
app.include_router(auth.router)
app.include_router(groups.router)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@app.post("/api/admin/purge", tags=["admin"])
async def trigger_purge(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    """Manually trigger the data-retention purge job (requires X-Admin-Key)."""
    expected = config.ADMIN_KEY
    if not expected or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key",
        )

    from app.jobs.purge_old_events import run_purge
    result = await run_purge()
    return {"ok": True, **result}


@app.get("/api/admin/config", tags=["admin"])
async def get_config_summary(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    """Return non-sensitive config summary (requires X-Admin-Key)."""
    expected = config.ADMIN_KEY
    if not expected or x_admin_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin key",
        )

    return {
        "environment": config.ENVIRONMENT,
        "signups_enabled": config.SIGNUPS_ENABLED,
        "purge_enabled": config.PURGE_ENABLED,
        "purge_retention_days": config.FREE_RETENTION_DAYS,
        "cors_origins": config.CORS_ORIGINS,
        "limits": config.get_tier_limits(),
    }
