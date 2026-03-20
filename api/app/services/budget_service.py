# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.budget import Budget, BudgetPeriod
from app.models.event import Event
from app.models.alert import Alert, AlertType
from app.schemas.budgets import BudgetCreate, BudgetUpdate
from app.services.alert_service import create_alert


async def create_budget(
    db: AsyncSession,
    user_id,
    data: BudgetCreate,
) -> Budget:
    """Create a new budget for a user."""
    budget = Budget(
        user_id=user_id,
        amount_usd=data.amount_usd,
        period=BudgetPeriod(data.period),
        alert_thresholds=data.alert_thresholds,
        is_active=True,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def get_budgets(
    db: AsyncSession,
    user_id,
) -> list[Budget]:
    """Get all budgets for a user."""
    q = select(Budget).where(Budget.user_id == user_id).order_by(Budget.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_budget(
    db: AsyncSession,
    budget_id,
    user_id,
) -> Budget | None:
    """Get a specific budget by ID, scoped to the user."""
    q = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def update_budget(
    db: AsyncSession,
    budget_id,
    user_id,
    data: BudgetUpdate,
) -> Budget | None:
    """Update fields on an existing budget."""
    budget = await get_budget(db, budget_id, user_id)
    if budget is None:
        return None

    if data.amount_usd is not None:
        budget.amount_usd = data.amount_usd
    if data.period is not None:
        budget.period = BudgetPeriod(data.period)
    if data.alert_thresholds is not None:
        budget.alert_thresholds = data.alert_thresholds
    if data.is_active is not None:
        budget.is_active = data.is_active

    await db.commit()
    await db.refresh(budget)
    return budget


async def delete_budget(
    db: AsyncSession,
    budget_id,
    user_id,
) -> bool:
    """Delete a budget. Returns True if deleted, False if not found."""
    budget = await get_budget(db, budget_id, user_id)
    if budget is None:
        return False
    await db.delete(budget)
    await db.commit()
    return True


async def get_current_spend(
    db: AsyncSession,
    user_id,
    period: str,
    team_id=None,
) -> float:
    """
    Sum cost_usd for events in the current period (day/week/month).
    Uses date_trunc to find events in the same calendar period as now.
    """
    now = datetime.now(timezone.utc)

    trunc_map = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
    }
    trunc_unit = trunc_map.get(period, "month")

    # Events where date_trunc(unit, created_at) = date_trunc(unit, now)
    period_start = func.date_trunc(trunc_unit, func.now())

    q = select(func.coalesce(func.sum(Event.cost_usd), 0)).where(
        Event.created_at >= period_start
    )

    if team_id is not None:
        q = q.where(Event.team_id == team_id)
    else:
        q = q.where(Event.user_id == user_id)

    result = await db.execute(q)
    value = result.scalar()
    return float(value) if value is not None else 0.0


async def check_budget_thresholds(
    db: AsyncSession,
    budget: Budget,
) -> list[Alert]:
    """
    Compare current spend against each threshold in the budget.
    Creates alerts for thresholds that have been crossed but not yet alerted.
    Returns newly created alerts.
    """
    user_id = budget.user_id
    team_id = budget.team_id

    spend = await get_current_spend(db, user_id, budget.period.value, team_id)
    limit = float(budget.amount_usd)
    if limit <= 0:
        return []

    utilization = spend / limit
    new_alerts = []

    for threshold in sorted(budget.alert_thresholds):
        if utilization < threshold:
            continue

        # Determine alert type
        alert_type = (
            AlertType.budget_exceeded if threshold >= 1.0 else AlertType.threshold_warning
        )

        # Check if we've already sent this alert for this threshold in the current period
        existing_q = (
            select(Alert)
            .where(
                Alert.budget_id == budget.id,
                Alert.threshold == threshold,
                Alert.type == alert_type,
            )
            .order_by(Alert.notified_at.desc())
            .limit(1)
        )
        result = await db.execute(existing_q)
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Already alerted for this threshold; skip
            continue

        alert = await create_alert(db, budget, threshold, alert_type)
        new_alerts.append(alert)

    return new_alerts
