# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Alert dispatcher — sends budget alerts to Slack, generic webhooks, or email (stub).

Rate-limits: same alert (budget_id + threshold) won't fire more than once per hour.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Redis key TTL for rate-limiting (seconds)
RATE_LIMIT_TTL = 3600  # 1 hour


def _rate_limit_key(budget_id: str, threshold: int) -> str:
    return f"alert:sent:{budget_id}:{threshold}"


async def is_rate_limited(redis, budget_id: str, threshold: int) -> bool:
    """Check if this alert was already sent within the rate-limit window."""
    if redis is None:
        return False
    key = _rate_limit_key(budget_id, threshold)
    return await redis.exists(key) > 0


async def mark_sent(redis, budget_id: str, threshold: int) -> None:
    """Record that this alert was sent, preventing duplicates for 1 hour."""
    if redis is None:
        return
    key = _rate_limit_key(budget_id, threshold)
    await redis.set(key, "1", ex=RATE_LIMIT_TTL)


def _build_payload(
    budget_name: str,
    current_spend: float,
    limit: float,
    percentage: float,
    project_name: str | None = None,
    triggered_at: str | None = None,
) -> dict:
    return {
        "budget_name": budget_name,
        "current_spend": round(current_spend, 2),
        "limit": round(limit, 2),
        "percentage": round(percentage, 2),
        "project_name": project_name or "default",
        "triggered_at": triggered_at or datetime.now(timezone.utc).isoformat(),
    }


async def send_slack(webhook_url: str, payload: dict) -> bool:
    """Post a Slack incoming-webhook message (no SDK, just httpx)."""
    slack_body = {
        "text": (
            f":warning: *Budget Alert — {payload['budget_name']}*\n"
            f"Spend: ${payload['current_spend']:.2f} / ${payload['limit']:.2f} "
            f"({payload['percentage']:.0f}%)\n"
            f"Project: {payload['project_name']}\n"
            f"Triggered: {payload['triggered_at']}"
        ),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=slack_body)
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Failed to send Slack alert to %s", webhook_url)
        return False


async def send_webhook(webhook_url: str, payload: dict) -> bool:
    """POST JSON payload to a user-configured generic webhook URL."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            return True
    except Exception:
        logger.exception("Failed to send webhook alert to %s", webhook_url)
        return False


async def send_email(webhook_url: str, payload: dict) -> bool:
    """Placeholder for future Resend email integration."""
    logger.info(
        "Email alert stub: would send to %s — %s", webhook_url, json.dumps(payload)
    )
    # Return True so tests/callers treat it as "delivered" (it's a stub).
    return True


CHANNEL_SENDERS = {
    "slack": send_slack,
    "webhook": send_webhook,
    "email": send_email,
}


async def dispatch_alert(
    channel_type: str,
    webhook_url: str,
    *,
    budget_name: str,
    current_spend: float,
    limit: float,
    percentage: float,
    project_name: str | None = None,
    triggered_at: str | None = None,
    redis=None,
    budget_id: str | None = None,
    threshold: int | None = None,
    db=None,
    budget=None,
) -> bool:
    """
    High-level dispatcher: build payload, check rate-limit, send via channel.

    Returns True if sent (or already rate-limited), False on send failure.
    """
    # Rate-limit check
    if budget_id and threshold is not None and redis is not None:
        if await is_rate_limited(redis, budget_id, threshold):
            logger.info(
                "Alert rate-limited: budget=%s threshold=%s", budget_id, threshold
            )
            return True  # already sent recently, treat as success

    payload = _build_payload(
        budget_name=budget_name,
        current_spend=current_spend,
        limit=limit,
        percentage=percentage,
        project_name=project_name,
        triggered_at=triggered_at,
    )

    sender = CHANNEL_SENDERS.get(channel_type)
    if sender is None:
        logger.error("Unknown channel type: %s", channel_type)
        return False

    success = await sender(webhook_url, payload)

    # Mark as sent on success
    if success and budget_id and threshold is not None and redis is not None:
        await mark_sent(redis, budget_id, threshold)

    # Record alert in database for history/audit trail
    if success and db is not None and budget is not None:
        from app.services.alert_service import create_alert
        from app.models.alert import AlertType

        alert_type = (
            AlertType.budget_exceeded if percentage >= 100
            else AlertType.budget_warning
        )
        try:
            await create_alert(db, budget, percentage / 100.0, alert_type)
        except Exception:
            logger.warning("Failed to record alert history for budget %s", budget_id)

    return success
