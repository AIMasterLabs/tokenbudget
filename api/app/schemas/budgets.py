# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BudgetCreate(BaseModel):
    amount_usd: float
    period: str  # "daily", "weekly", "monthly"
    alert_thresholds: list[float] = [0.8, 1.0]


class BudgetUpdate(BaseModel):
    amount_usd: float | None = None
    period: str | None = None
    alert_thresholds: list[float] | None = None
    is_active: bool | None = None


class BudgetResponse(BaseModel):
    id: str
    amount_usd: float
    period: str
    alert_thresholds: list[float]
    is_active: bool
    current_spend_usd: float = 0.0
    utilization_pct: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
