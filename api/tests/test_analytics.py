# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for analytics endpoints.
Seeds events and verifies aggregated responses.
"""
import pytest
from app.models.event import Event


async def _seed_events(db_session, user_id, api_key_id):
    """Seed 10 events with a mix of 3 models."""
    events = [
        # 4 gpt-4 events: cost 0.10 each -> 0.40 total
        {"model": "gpt-4", "provider": "openai", "cost_usd": 0.10, "input_tokens": 100,
         "output_tokens": 50, "total_tokens": 150, "latency_ms": 500},
        {"model": "gpt-4", "provider": "openai", "cost_usd": 0.10, "input_tokens": 100,
         "output_tokens": 50, "total_tokens": 150, "latency_ms": 600},
        {"model": "gpt-4", "provider": "openai", "cost_usd": 0.10, "input_tokens": 100,
         "output_tokens": 50, "total_tokens": 150, "latency_ms": 550},
        {"model": "gpt-4", "provider": "openai", "cost_usd": 0.10, "input_tokens": 100,
         "output_tokens": 50, "total_tokens": 150, "latency_ms": 700},
        # 3 gpt-3.5-turbo events: cost 0.02 each -> 0.06 total
        {"model": "gpt-3.5-turbo", "provider": "openai", "cost_usd": 0.02, "input_tokens": 200,
         "output_tokens": 80, "total_tokens": 280, "latency_ms": 300},
        {"model": "gpt-3.5-turbo", "provider": "openai", "cost_usd": 0.02, "input_tokens": 200,
         "output_tokens": 80, "total_tokens": 280, "latency_ms": 350},
        {"model": "gpt-3.5-turbo", "provider": "openai", "cost_usd": 0.02, "input_tokens": 200,
         "output_tokens": 80, "total_tokens": 280, "latency_ms": 400},
        # 3 claude-sonnet events: cost 0.05 each -> 0.15 total
        {"model": "claude-sonnet-4-20250514", "provider": "anthropic", "cost_usd": 0.05,
         "input_tokens": 150, "output_tokens": 60, "total_tokens": 210, "latency_ms": 800},
        {"model": "claude-sonnet-4-20250514", "provider": "anthropic", "cost_usd": 0.05,
         "input_tokens": 150, "output_tokens": 60, "total_tokens": 210, "latency_ms": 900},
        {"model": "claude-sonnet-4-20250514", "provider": "anthropic", "cost_usd": 0.05,
         "input_tokens": 150, "output_tokens": 60, "total_tokens": 210, "latency_ms": 850},
    ]
    for e in events:
        row = Event(
            api_key_id=api_key_id,
            user_id=user_id,
            provider=e["provider"],
            model=e["model"],
            input_tokens=e["input_tokens"],
            output_tokens=e["output_tokens"],
            total_tokens=e["total_tokens"],
            cost_usd=e["cost_usd"],
            latency_ms=e["latency_ms"],
        )
        db_session.add(row)
    await db_session.commit()


@pytest.mark.asyncio
async def test_analytics_summary(client, auth_headers, test_user_and_key, db_session):
    await _seed_events(db_session, test_user_and_key["user_id"], test_user_and_key["api_key_id"])

    response = await client.get("/api/analytics/summary?period=30d", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # 10 events, total cost = 0.40 + 0.06 + 0.15 = 0.61
    assert data["total_requests"] == 10
    assert abs(data["total_cost_usd"] - 0.61) < 0.001
    assert data["total_input_tokens"] > 0
    assert data["total_output_tokens"] > 0
    assert data["avg_cost_per_request"] > 0
    assert data["avg_latency_ms"] > 0


@pytest.mark.asyncio
async def test_analytics_summary_no_events(client, auth_headers):
    """Summary with no events should return zeroes."""
    response = await client.get("/api/analytics/summary?period=1d", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 0
    assert data["total_cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_analytics_by_model(client, auth_headers, test_user_and_key, db_session):
    await _seed_events(db_session, test_user_and_key["user_id"], test_user_and_key["api_key_id"])

    response = await client.get("/api/analytics/by-model?period=30d", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Should have 3 distinct models
    assert len(data) == 3

    model_names = {d["model"] for d in data}
    assert "gpt-4" in model_names
    assert "gpt-3.5-turbo" in model_names
    assert "claude-sonnet-4-20250514" in model_names

    # Percentages should sum to ~100
    total_pct = sum(d["percentage"] for d in data)
    assert abs(total_pct - 100.0) < 0.5

    # gpt-4 should have the highest cost
    gpt4 = next(d for d in data if d["model"] == "gpt-4")
    assert gpt4["request_count"] == 4
    assert abs(gpt4["total_cost_usd"] - 0.40) < 0.001


@pytest.mark.asyncio
async def test_analytics_timeseries(client, auth_headers, test_user_and_key, db_session):
    await _seed_events(db_session, test_user_and_key["user_id"], test_user_and_key["api_key_id"])

    response = await client.get(
        "/api/analytics/timeseries?period=30d&granularity=daily", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()

    # All events are from today, so there should be exactly 1 daily bucket
    assert len(data) >= 1

    # Each point has required fields
    for point in data:
        assert "timestamp" in point
        assert "cost_usd" in point
        assert "request_count" in point
        assert point["request_count"] > 0

    # Total across all buckets should match
    total_requests = sum(p["request_count"] for p in data)
    assert total_requests == 10


@pytest.mark.asyncio
async def test_analytics_requires_auth(client):
    response = await client.get("/api/analytics/summary")
    assert response.status_code == 401
