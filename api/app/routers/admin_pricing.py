# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Admin endpoint for syncing pricing from LiteLLM.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.config import config
from app.lib.pricing_sync import sync_from_litellm, generate_pricing_snippet

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/sync-pricing")
async def sync_pricing(admin_key: str = Header(..., alias="X-Admin-Key")):
    """
    Fetch latest model pricing from LiteLLM's public repo.

    Requires the X-Admin-Key header matching the ADMIN_KEY env var.
    Returns the fetched pricing data and a Python snippet that can be
    pasted into pricing.py.
    """
    if not config.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin key not configured",
        )
    if admin_key != config.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

    try:
        result = await sync_from_litellm()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch pricing from LiteLLM: {exc}",
        )

    snippet = generate_pricing_snippet(result["pricing"])

    return {
        "status": "ok",
        "models_fetched": result["models_fetched"],
        "pricing_snippet_preview": snippet[:2000],
    }
