# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Price change detection endpoints.

GET  /api/price-changes       — list recent price changes (last 30 days)
GET  /api/price-changes/check — manually trigger a check (admin only)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database import get_db
from app.lib.pricing import _PRICING
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.price_change import PriceChange
from app.models.user import User
from app.schemas.price_changes import PriceChangeResponse, PriceCheckResult
from app.services.price_monitor import detect_price_changes, store_price_changes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/price-changes", tags=["price-changes"])


def _to_response(pc: PriceChange) -> PriceChangeResponse:
    return PriceChangeResponse(
        id=str(pc.id),
        provider=pc.provider,
        model=pc.model,
        old_input_price=pc.old_input_price,
        new_input_price=pc.new_input_price,
        old_output_price=pc.old_output_price,
        new_output_price=pc.new_output_price,
        detected_at=pc.detected_at,
        notified=pc.notified,
    )


@router.get("", response_model=list[PriceChangeResponse])
async def list_price_changes(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """List price changes detected in the last 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(PriceChange)
        .where(PriceChange.detected_at >= cutoff)
        .order_by(PriceChange.detected_at.desc())
    )
    records = result.scalars().all()
    return [_to_response(r) for r in records]


async def _require_admin(
    x_admin_key: str | None = Header(None),
) -> None:
    """Dependency that checks for a valid admin key."""
    if not config.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin key not configured",
        )
    if x_admin_key != config.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )


@router.get("/check", response_model=PriceCheckResult)
async def check_price_changes(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    _admin: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a price check against LiteLLM pricing data.

    Requires both a valid API key and the admin key (X-Admin-Key header).
    Compares current built-in pricing with LiteLLM's latest data.
    """
    try:
        import litellm  # type: ignore[import-untyped]
        litellm_prices: dict[str, tuple[float, float]] = {}
        model_cost = getattr(litellm, "model_cost", {})
        for model_key, info in model_cost.items():
            if isinstance(info, dict):
                # LiteLLM stores prices per token; convert to per 1K
                input_price = info.get("input_cost_per_token", 0.0) * 1000
                output_price = info.get("output_cost_per_token", 0.0) * 1000
                # Only compare models we track
                normalized = model_key.strip().lower()
                if normalized in _PRICING:
                    litellm_prices[normalized] = (input_price, output_price)
    except ImportError:
        logger.warning("litellm not installed — using empty comparison set")
        litellm_prices = {}

    if not litellm_prices:
        return PriceCheckResult(changes_detected=0, changes=[])

    changes = detect_price_changes(_PRICING, litellm_prices)

    if changes:
        records = await store_price_changes(changes, db)
        return PriceCheckResult(
            changes_detected=len(records),
            changes=[_to_response(r) for r in records],
        )

    return PriceCheckResult(changes_detected=0, changes=[])
