# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.config import config
from app.database import get_db
from app.models.waitlist import Waitlist

router = APIRouter()


class WaitlistRequest(BaseModel):
    email: str
    source: str = "landing"


class WaitlistResponse(BaseModel):
    message: str
    email: str


@router.post("/api/waitlist", response_model=WaitlistResponse)
async def join_waitlist(data: WaitlistRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Waitlist).where(Waitlist.email == data.email))
    if existing.scalar_one_or_none():
        return WaitlistResponse(message="You're already on the list!", email=data.email)

    entry = Waitlist(email=data.email, source=data.source)
    db.add(entry)
    await db.commit()
    return WaitlistResponse(message="You're on the list! We'll be in touch.", email=data.email)


@router.get("/api/waitlist")
async def list_waitlist(
    admin_key: str = Header(alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    expected = config.ADMIN_KEY
    if admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    result = await db.execute(select(Waitlist).order_by(Waitlist.created_at.desc()))
    entries = result.scalars().all()
    return [{"email": e.email, "source": e.source, "created_at": str(e.created_at)} for e in entries]
