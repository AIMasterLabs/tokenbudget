# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Pydantic schemas for price change endpoints."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PriceChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    model: str
    old_input_price: float
    new_input_price: float
    old_output_price: float
    new_output_price: float
    detected_at: datetime
    notified: bool


class PriceCheckResult(BaseModel):
    changes_detected: int
    changes: list[PriceChangeResponse]
