# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/v1", tags=["pricing"])

PRICING_DATA = {
    "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
    "gpt-4-turbo": {"input_per_1k": 0.01, "output_per_1k": 0.03},
    "gpt-4o": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gpt-3.5-turbo": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
    "o1": {"input_per_1k": 0.015, "output_per_1k": 0.060, "reasoning_per_1k": 0.060},
    "o3": {"input_per_1k": 0.010, "output_per_1k": 0.040, "reasoning_per_1k": 0.040},
    "o3-mini": {"input_per_1k": 0.0011, "output_per_1k": 0.0044, "reasoning_per_1k": 0.0044},
    "o4-mini": {"input_per_1k": 0.0011, "output_per_1k": 0.0044, "reasoning_per_1k": 0.0044},
    "claude-sonnet-4-20250514": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-opus-4-20250514": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "claude-haiku-4-5-20251001": {"input_per_1k": 0.0008, "output_per_1k": 0.004},
}

UPDATED_AT = datetime(2026, 3, 19, 0, 0, 0, tzinfo=timezone.utc)


@router.get("/pricing")
async def get_pricing():
    return {
        "models": PRICING_DATA,
        "updated_at": UPDATED_AT.isoformat(),
    }
