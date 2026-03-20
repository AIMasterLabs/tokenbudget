# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.budgets import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


async def _enrich_budget(db, budget, user_id) -> BudgetResponse:
    """Add current spend and utilization to a budget response."""
    spend = await budget_service.get_current_spend(
        db, user_id=user_id, period=budget.period.value, team_id=budget.team_id
    )
    limit = float(budget.amount_usd)
    utilization = (spend / limit * 100) if limit > 0 else 0.0

    return BudgetResponse(
        id=str(budget.id),
        amount_usd=limit,
        period=budget.period.value,
        alert_thresholds=budget.alert_thresholds,
        is_active=budget.is_active,
        current_spend_usd=spend,
        utilization_pct=round(utilization, 2),
        created_at=budget.created_at,
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    budget = await budget_service.create_budget(db, user_id=user.id, data=data)
    return await _enrich_budget(db, budget, user.id)


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    budgets = await budget_service.get_budgets(db, user_id=user.id)
    return [await _enrich_budget(db, b, user.id) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    budget = await budget_service.get_budget(db, budget_id=budget_id, user_id=user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return await _enrich_budget(db, budget, user.id)


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    budget = await budget_service.update_budget(
        db, budget_id=budget_id, user_id=user.id, data=data
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return await _enrich_budget(db, budget, user.id)


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    deleted = await budget_service.delete_budget(db, budget_id=budget_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return {"deleted": True}


@router.get("/{budget_id}/status")
async def get_budget_status(
    budget_id: uuid.UUID,
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    _, user = auth
    budget = await budget_service.get_budget(db, budget_id=budget_id, user_id=user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    spend = await budget_service.get_current_spend(
        db, user_id=user.id, period=budget.period.value, team_id=budget.team_id
    )
    limit = float(budget.amount_usd)
    pct = (spend / limit * 100) if limit > 0 else 0.0

    return {
        "spend_usd": spend,
        "limit_usd": limit,
        "pct": round(pct, 2),
    }
