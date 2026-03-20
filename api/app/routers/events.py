# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.events import EventCreate, EventBatch
from app.services.event_service import create_event, create_events_batch
from app.lib.tier_check import check_event_quota

router = APIRouter(prefix="/v1", tags=["events"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(
    event_data: EventCreate,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    api_key, user = auth
    await check_event_quota(db, user.id, tier="free")
    await create_event(db, event_data, api_key)
    return {"accepted": True}


@router.post("/events/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events_batch(
    batch: EventBatch,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    api_key, user = auth
    await check_event_quota(db, user.id, tier="free")
    await create_events_batch(db, batch.events, api_key)
    return {"accepted": True, "count": len(batch.events)}
