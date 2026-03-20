# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel
from datetime import datetime


class AnalyticsSummary(BaseModel):
    total_cost_usd: float
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_reasoning_tokens: int = 0
    avg_cost_per_request: float
    avg_latency_ms: float


class ModelBreakdown(BaseModel):
    model: str
    total_cost_usd: float
    request_count: int
    percentage: float  # of total cost


class UserBreakdown(BaseModel):
    user_id: str
    email: str | None = None
    total_cost_usd: float
    request_count: int


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    cost_usd: float
    request_count: int


class TagBreakdown(BaseModel):
    tag_value: str
    total_cost_usd: float
    request_count: int


class UsageSummary(BaseModel):
    tier: str
    events_this_month: int
    events_limit: int
    events_pct: float
    active_keys: int
    keys_limit: int
    keys_pct: float
    retention_days: int
    projects_limit: int
