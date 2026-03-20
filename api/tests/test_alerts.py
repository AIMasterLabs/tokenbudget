# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for alert configuration endpoints and alert dispatcher.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


BUDGET_PAYLOAD = {
    "amount_usd": 100.0,
    "period": "monthly",
    "alert_thresholds": [0.8, 1.0],
}


@pytest.mark.asyncio
async def test_create_alert_config(client, auth_headers):
    """Create an alert config for a budget."""
    # First create a budget to attach the alert to
    budget_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    assert budget_resp.status_code == 201
    budget_id = budget_resp.json()["id"]

    alert_payload = {
        "channel_type": "webhook",
        "webhook_url": "https://example.com/hook",
        "budget_id": budget_id,
        "thresholds": [50, 80, 100],
    }
    resp = await client.post("/api/alerts", json=alert_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel_type"] == "webhook"
    assert data["webhook_url"] == "https://example.com/hook"
    assert data["budget_id"] == budget_id
    assert data["thresholds"] == [50, 80, 100]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_alert_configs(client, auth_headers):
    """List alert configs returns created configs."""
    budget_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = budget_resp.json()["id"]

    # Create two alert configs
    for url in ["https://example.com/hook1", "https://example.com/hook2"]:
        await client.post(
            "/api/alerts",
            json={
                "channel_type": "webhook",
                "webhook_url": url,
                "budget_id": budget_id,
                "thresholds": [80, 100],
            },
            headers=auth_headers,
        )

    resp = await client.get("/api/alerts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_delete_alert_config(client, auth_headers):
    """Delete an alert config."""
    budget_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = budget_resp.json()["id"]

    create_resp = await client.post(
        "/api/alerts",
        json={
            "channel_type": "slack",
            "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
            "budget_id": budget_id,
            "thresholds": [50, 80, 100],
        },
        headers=auth_headers,
    )
    config_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/alerts/{config_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"deleted": True}

    # Verify it's gone from the list
    list_resp = await client.get("/api/alerts", headers=auth_headers)
    ids = [c["id"] for c in list_resp.json()]
    assert config_id not in ids


@pytest.mark.asyncio
async def test_delete_alert_config_not_found(client, auth_headers):
    """Deleting non-existent config returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/alerts/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_channel_type(client, auth_headers):
    """Creating alert with invalid channel_type returns 400."""
    budget_resp = await client.post("/api/budgets", json=BUDGET_PAYLOAD, headers=auth_headers)
    budget_id = budget_resp.json()["id"]

    resp = await client.post(
        "/api/alerts",
        json={
            "channel_type": "sms",
            "webhook_url": "https://example.com",
            "budget_id": budget_id,
            "thresholds": [80],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_test_alert_webhook(client, auth_headers):
    """POST /api/alerts/test sends a test message via webhook (mocked)."""
    with patch("app.routers.alerts.dispatch_alert", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = True
        resp = await client.post(
            "/api/alerts/test",
            json={
                "channel_type": "webhook",
                "webhook_url": "https://example.com/hook",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "sent successfully" in data["message"]
        mock_dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_test_alert_failure(client, auth_headers):
    """POST /api/alerts/test returns failure when dispatch fails."""
    with patch("app.routers.alerts.dispatch_alert", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = False
        resp = await client.post(
            "/api/alerts/test",
            json={
                "channel_type": "webhook",
                "webhook_url": "https://example.com/bad-hook",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


@pytest.mark.asyncio
async def test_dispatcher_sends_webhook():
    """Alert dispatcher POSTs JSON to webhook URL."""
    from app.services.alert_dispatcher import dispatch_alert

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.alert_dispatcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await dispatch_alert(
            channel_type="webhook",
            webhook_url="https://example.com/hook",
            budget_name="My Budget",
            current_spend=80.0,
            limit=100.0,
            percentage=80.0,
        )
        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://example.com/hook"
        payload = call_args[1]["json"]
        assert payload["budget_name"] == "My Budget"
        assert payload["current_spend"] == 80.0


@pytest.mark.asyncio
async def test_dispatcher_sends_slack():
    """Alert dispatcher POSTs Slack-formatted message."""
    from app.services.alert_dispatcher import dispatch_alert

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.alert_dispatcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await dispatch_alert(
            channel_type="slack",
            webhook_url="https://hooks.slack.com/services/T00/B00/xxx",
            budget_name="Slack Budget",
            current_spend=90.0,
            limit=100.0,
            percentage=90.0,
        )
        assert result is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert "text" in payload
        assert "Slack Budget" in payload["text"]


@pytest.mark.asyncio
async def test_dispatcher_rate_limiting():
    """Same alert (budget_id + threshold) is rate-limited within 1 hour."""
    from app.services.alert_dispatcher import dispatch_alert

    mock_redis = AsyncMock()
    # First call: not rate-limited
    mock_redis.exists.return_value = 0

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.alert_dispatcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # First dispatch — should send
        result = await dispatch_alert(
            channel_type="webhook",
            webhook_url="https://example.com/hook",
            budget_name="Budget",
            current_spend=80.0,
            limit=100.0,
            percentage=80.0,
            redis=mock_redis,
            budget_id="budget-123",
            threshold=80,
        )
        assert result is True
        assert mock_client.post.call_count == 1
        mock_redis.set.assert_called_once()

    # Second call: rate-limited
    mock_redis.exists.return_value = 1

    with patch("app.services.alert_dispatcher.httpx.AsyncClient") as mock_client_cls2:
        mock_client2 = AsyncMock()
        mock_client_cls2.return_value = mock_client2

        result2 = await dispatch_alert(
            channel_type="webhook",
            webhook_url="https://example.com/hook",
            budget_name="Budget",
            current_spend=80.0,
            limit=100.0,
            percentage=80.0,
            redis=mock_redis,
            budget_id="budget-123",
            threshold=80,
        )
        assert result2 is True  # rate-limited returns True
        # httpx client should NOT have been used
        mock_client2.post.assert_not_called()


@pytest.mark.asyncio
async def test_dispatcher_email_stub():
    """Email channel returns True (stub)."""
    from app.services.alert_dispatcher import dispatch_alert

    result = await dispatch_alert(
        channel_type="email",
        webhook_url="user@example.com",
        budget_name="Email Budget",
        current_spend=50.0,
        limit=100.0,
        percentage=50.0,
    )
    assert result is True


@pytest.mark.asyncio
async def test_alerts_require_auth(client):
    """Unauthenticated requests to /api/alerts return 401."""
    resp = await client.get("/api/alerts")
    assert resp.status_code == 401
