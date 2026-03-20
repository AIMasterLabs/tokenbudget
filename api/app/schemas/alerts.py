# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class AlertConfigCreate(BaseModel):
    channel_type: str  # "slack", "webhook", "email"
    webhook_url: str
    budget_id: str
    thresholds: list[int] = [50, 80, 100]


class AlertConfigResponse(BaseModel):
    id: str
    budget_id: str
    channel_type: str
    webhook_url: str
    thresholds: list[int]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestAlertRequest(BaseModel):
    channel_type: str  # "slack", "webhook", "email"
    webhook_url: str


class TestAlertResponse(BaseModel):
    success: bool
    message: str
