# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Nightly purge job — deletes events older than the retention window.

Since we don't have per-user tiers yet, FREE_RETENTION_DAYS is used for all users.
Runs in batches of PURGE_BATCH_SIZE rows to avoid table locks on large tables.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import config
from app.models.event import Event

logger = logging.getLogger(__name__)


async def run_purge() -> dict:
    """
    Delete all events older than FREE_RETENTION_DAYS in batches.

    Returns a summary dict: {"deleted": int, "batches": int, "retention_days": int}.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.FREE_RETENTION_DAYS)

    engine = create_async_engine(config.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_deleted = 0
    batches = 0

    try:
        async with factory() as session:
            while True:
                # Select a batch of IDs to delete
                subq = (
                    select(Event.id)
                    .where(Event.created_at < cutoff)
                    .limit(config.PURGE_BATCH_SIZE)
                )
                result = await session.execute(subq)
                ids = [row[0] for row in result.fetchall()]

                if not ids:
                    break

                stmt = delete(Event).where(Event.id.in_(ids))
                del_result = await session.execute(stmt)
                await session.commit()

                deleted_this_batch = del_result.rowcount
                total_deleted += deleted_this_batch
                batches += 1

                logger.info(
                    "Purge batch %d: deleted %d events (total so far: %d)",
                    batches,
                    deleted_this_batch,
                    total_deleted,
                )

                if deleted_this_batch < config.PURGE_BATCH_SIZE:
                    # Last partial batch — done
                    break
    finally:
        await engine.dispose()

    logger.info(
        "Purge complete: deleted %d events in %d batches (retention=%d days)",
        total_deleted,
        batches,
        config.FREE_RETENTION_DAYS,
    )
    return {
        "deleted": total_deleted,
        "batches": batches,
        "retention_days": config.FREE_RETENTION_DAYS,
    }
