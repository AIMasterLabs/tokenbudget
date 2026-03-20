# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.config import config


class EventCreate(BaseModel):
    provider: str = Field(..., max_length=100)
    model: str = Field(..., max_length=config.MAX_MODEL_LEN)
    input_tokens: int = Field(..., ge=0, le=config.MAX_INPUT_TOKENS)
    output_tokens: int = Field(..., ge=0, le=config.MAX_OUTPUT_TOKENS)
    reasoning_tokens: Optional[int] = Field(default=0, ge=0, le=config.MAX_OUTPUT_TOKENS)
    total_tokens: int = Field(..., ge=0, le=config.MAX_TOTAL_TOKENS)
    cost_usd: float = Field(..., ge=0.0, le=config.MAX_COST_USD)
    latency_ms: Optional[int] = Field(default=None, ge=0, le=config.MAX_LATENCY_MS)
    tags: Optional[dict] = None
    metadata: Optional[dict] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in config.VALID_PROVIDERS:
            raise ValueError(
                f"provider must be one of: {', '.join(config.VALID_PROVIDERS)}"
            )
        return v


class EventBatch(BaseModel):
    events: list[EventCreate]
