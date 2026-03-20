# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.alert import Alert, AlertType
from app.models.budget import Budget


async def create_alert(
    db: AsyncSession,
    budget: Budget,
    threshold: float,
    alert_type: AlertType,
) -> Alert:
    """Create an alert record for a budget threshold breach."""
    if alert_type == AlertType.budget_exceeded:
        message = f"Budget exceeded: spending has reached 100% of ${float(budget.amount_usd):.2f} limit"
    else:
        message = (
            f"Budget warning: spending has reached {int(threshold * 100)}% "
            f"of ${float(budget.amount_usd):.2f} limit"
        )

    alert = Alert(
        budget_id=budget.id,
        team_id=budget.team_id,
        user_id=budget.user_id,
        type=alert_type,
        threshold=threshold,
        message=message,
        notified_at=datetime.now(timezone.utc),
        channels=[],
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_alerts(
    db: AsyncSession,
    user_id,
    limit: int = 20,
) -> list[Alert]:
    """Get recent alerts for a user, ordered by most recent first."""
    q = (
        select(Alert)
        .where(Alert.user_id == user_id)
        .order_by(desc(Alert.notified_at))
        .limit(limit)
    )
    result = await db.execute(q)
    return list(result.scalars().all())
