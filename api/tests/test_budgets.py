# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for budget management endpoints and threshold alert checking.
"""
import pytest
from app.models.event import Event
from app.models.budget import BudgetPeriod
from app.services.budget_service import check_budget_thresholds, get_current_spend


BUDGET_PAYLOAD = {
    "amount_usd": 100.0,
    "period": "monthly",
    "alert_thresholds": [0.8, 1.0],
}


@pytest.mark.asyncio
async def test_create_budget(client, auth_headers):
    response = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["amount_usd"] == 100.0
    assert data["period"] == "monthly"
    assert data["is_active"] is True
    assert data["alert_thresholds"] == [0.8, 1.0]
    assert "id" in data
    assert "created_at" in data
    assert "current_spend_usd" in data
    assert "utilization_pct" in data


@pytest.mark.asyncio
async def test_list_budgets(client, auth_headers):
    # Create two budgets
    await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    await client.post(
        "/api/budgets",
        json={"amount_usd": 50.0, "period": "daily", "alert_thresholds": [0.9]},
        headers=auth_headers,
    )

    response = await client.get("/api/budgets", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_budget_by_id(client, auth_headers):
    create_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = create_resp.json()["id"]

    response = await client.get(f"/api/budgets/{budget_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == budget_id
    assert data["amount_usd"] == 100.0


@pytest.mark.asyncio
async def test_get_budget_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/budgets/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_budget(client, auth_headers):
    create_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/budgets/{budget_id}",
        json={"amount_usd": 200.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount_usd"] == 200.0


@pytest.mark.asyncio
async def test_delete_budget(client, auth_headers):
    create_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/budgets/{budget_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"deleted": True}

    # Subsequent GET should 404
    get_resp = await client.get(f"/api/budgets/{budget_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_budget_status_endpoint(client, auth_headers):
    create_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = create_resp.json()["id"]

    response = await client.get(f"/api/budgets/{budget_id}/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "spend_usd" in data
    assert "limit_usd" in data
    assert "pct" in data
    assert data["limit_usd"] == 100.0


@pytest.mark.asyncio
async def test_budget_threshold_triggers_alert(test_user_and_key, db_session):
    """
    Seed events totaling $80 spend for a $100 monthly budget with 0.8 threshold.
    check_budget_thresholds() should create one alert.
    """
    from app.services.budget_service import create_budget, check_budget_thresholds
    from app.schemas.budgets import BudgetCreate

    user_id = test_user_and_key["user_id"]
    api_key_id = test_user_and_key["api_key_id"]

    # Seed events totaling $80 in the current month
    for _ in range(8):
        event = Event(
            api_key_id=api_key_id,
            user_id=user_id,
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=10.0,  # $10 each -> $80 total for 8
            latency_ms=500,
        )
        db_session.add(event)
    await db_session.commit()

    # Create a $100 monthly budget with 0.8 threshold
    budget = await create_budget(
        db_session,
        user_id=user_id,
        data=BudgetCreate(amount_usd=100.0, period="monthly", alert_thresholds=[0.8]),
    )

    # Check thresholds - should trigger the 80% alert
    alerts = await check_budget_thresholds(db_session, budget)

    assert len(alerts) == 1
    assert float(alerts[0].threshold) == 0.8
    assert alerts[0].budget_id == budget.id
    assert alerts[0].user_id == user_id


@pytest.mark.asyncio
async def test_budget_threshold_not_triggered_below_threshold(test_user_and_key, db_session):
    """
    With only $50 spend on a $100 budget, 0.8 threshold should NOT trigger.
    """
    from app.services.budget_service import create_budget, check_budget_thresholds
    from app.schemas.budgets import BudgetCreate

    user_id = test_user_and_key["user_id"]
    api_key_id = test_user_and_key["api_key_id"]

    # Seed $50 worth of events
    for _ in range(5):
        event = Event(
            api_key_id=api_key_id,
            user_id=user_id,
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=10.0,
            latency_ms=500,
        )
        db_session.add(event)
    await db_session.commit()

    budget = await create_budget(
        db_session,
        user_id=user_id,
        data=BudgetCreate(amount_usd=100.0, period="monthly", alert_thresholds=[0.8, 1.0]),
    )

    alerts = await check_budget_thresholds(db_session, budget)
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_budget_requires_auth(client):
    response = await client.get("/api/budgets")
    assert response.status_code == 401
