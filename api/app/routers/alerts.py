# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.user import User
from app.models.alert_config import AlertConfig, ChannelType
from app.schemas.alerts import (
    AlertConfigCreate,
    AlertConfigResponse,
    TestAlertRequest,
    TestAlertResponse,
)
from app.services.alert_dispatcher import dispatch_alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _to_response(cfg: AlertConfig) -> AlertConfigResponse:
    return AlertConfigResponse(
        id=str(cfg.id),
        budget_id=str(cfg.budget_id),
        channel_type=cfg.channel_type.value,
        webhook_url=cfg.webhook_url,
        thresholds=cfg.thresholds,
        is_active=cfg.is_active,
        created_at=cfg.created_at,
    )


@router.get("", response_model=list[AlertConfigResponse])
async def list_alert_configs(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    result = await db.execute(
        select(AlertConfig)
        .where(AlertConfig.user_id == user.id)
        .order_by(AlertConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return [_to_response(c) for c in configs]


@router.post("", response_model=AlertConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_config(
    data: AlertConfigCreate,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth

    # Validate channel_type
    try:
        channel = ChannelType(data.channel_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel_type. Must be one of: {[t.value for t in ChannelType]}",
        )

    # Validate budget_id is a valid UUID
    try:
        budget_uuid = uuid.UUID(data.budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid budget_id format",
        )

    cfg = AlertConfig(
        user_id=user.id,
        budget_id=budget_uuid,
        channel_type=channel,
        webhook_url=data.webhook_url,
        thresholds=data.thresholds,
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _to_response(cfg)


@router.delete("/{config_id}")
async def delete_alert_config(
    config_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    result = await db.execute(
        select(AlertConfig).where(
            AlertConfig.id == config_id,
            AlertConfig.user_id == user.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert config not found",
        )
    await db.delete(cfg)
    await db.commit()
    return {"deleted": True}


@router.post("/test", response_model=TestAlertResponse)
async def test_alert(
    data: TestAlertRequest,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
):
    """Send a test alert to verify webhook works."""
    success = await dispatch_alert(
        channel_type=data.channel_type,
        webhook_url=data.webhook_url,
        budget_name="Test Budget",
        current_spend=42.50,
        limit=100.00,
        percentage=42.5,
        project_name="test-project",
    )
    if success:
        return TestAlertResponse(success=True, message="Test alert sent successfully")
    return TestAlertResponse(success=False, message="Failed to deliver test alert")
