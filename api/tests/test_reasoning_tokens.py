# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for reasoning model token tracking (o1, o3, o4-mini, Claude thinking).
"""
import pytest
from app.lib.pricing import calculate_cost


# ---------------------------------------------------------------------------
# Cost calculation tests
# ---------------------------------------------------------------------------


class TestReasoningCostCalculation:
    """Verify that reasoning_tokens are billed at the output rate."""

    def test_o1_no_reasoning(self):
        # o1: input $0.015/1K, output $0.060/1K
        cost = calculate_cost("o1", input_tokens=1000, output_tokens=1000)
        assert abs(cost - 0.075) < 1e-6  # 0.015 + 0.060

    def test_o1_with_reasoning(self):
        # reasoning_tokens billed at output rate ($0.060/1K)
        cost = calculate_cost("o1", input_tokens=1000, output_tokens=500, reasoning_tokens=500)
        # 0.015 + (500/1000)*0.060 + (500/1000)*0.060 = 0.015 + 0.030 + 0.030 = 0.075
        assert abs(cost - 0.075) < 1e-6

    def test_o3_with_reasoning(self):
        # o3: input $0.010/1K, output $0.040/1K
        cost = calculate_cost("o3", input_tokens=2000, output_tokens=1000, reasoning_tokens=3000)
        # (2000/1000)*0.010 + (1000/1000)*0.040 + (3000/1000)*0.040
        # = 0.020 + 0.040 + 0.120 = 0.180
        assert abs(cost - 0.180) < 1e-6

    def test_o3_mini_with_reasoning(self):
        # o3-mini: input $0.0011/1K, output $0.0044/1K
        cost = calculate_cost("o3-mini", input_tokens=1000, output_tokens=1000, reasoning_tokens=2000)
        # 0.0011 + 0.0044 + (2000/1000)*0.0044 = 0.0011 + 0.0044 + 0.0088 = 0.0143
        assert abs(cost - 0.0143) < 1e-6

    def test_o4_mini_with_reasoning(self):
        # o4-mini: input $0.0011/1K, output $0.0044/1K
        cost = calculate_cost("o4-mini", input_tokens=1000, output_tokens=500, reasoning_tokens=1500)
        # 0.0011 + (500/1000)*0.0044 + (1500/1000)*0.0044
        # = 0.0011 + 0.0022 + 0.0066 = 0.0099
        assert abs(cost - 0.0099) < 1e-6

    def test_claude_thinking_tokens(self):
        # claude-sonnet-4: input $0.003/1K, output $0.015/1K
        cost = calculate_cost("claude-sonnet-4", input_tokens=1000, output_tokens=500, reasoning_tokens=1000)
        # 0.003 + (500/1000)*0.015 + (1000/1000)*0.015 = 0.003 + 0.0075 + 0.015 = 0.0255
        assert abs(cost - 0.0255) < 1e-6

    def test_non_reasoning_model_ignores_reasoning_tokens(self):
        # gpt-4o should NOT add reasoning cost even if reasoning_tokens passed
        cost_without = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=1000)
        cost_with = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=1000, reasoning_tokens=500)
        assert cost_without == cost_with

    def test_reasoning_zero_default(self):
        # Default reasoning_tokens=0 should produce same result as explicit 0
        cost_default = calculate_cost("o1", input_tokens=1000, output_tokens=1000)
        cost_explicit = calculate_cost("o1", input_tokens=1000, output_tokens=1000, reasoning_tokens=0)
        assert cost_default == cost_explicit

    def test_o1_versioned_suffix(self):
        # Versioned model name should still match
        cost = calculate_cost("o1-2025-04-16", input_tokens=1000, output_tokens=1000, reasoning_tokens=500)
        expected = 0.015 + 0.060 + (500 / 1000) * 0.060  # 0.015 + 0.060 + 0.030 = 0.105
        assert abs(cost - expected) < 1e-6


# ---------------------------------------------------------------------------
# Event ingestion tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_with_reasoning_tokens_accepted(client, auth_headers):
    """POST /v1/events should accept reasoning_tokens field."""
    payload = {
        "provider": "openai",
        "model": "o1",
        "input_tokens": 100,
        "output_tokens": 50,
        "reasoning_tokens": 200,
        "total_tokens": 350,
        "cost_usd": 0.02,
    }
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 202
    assert response.json()["accepted"] is True


@pytest.mark.asyncio
async def test_event_without_reasoning_tokens_defaults_zero(client, auth_headers):
    """Events without reasoning_tokens should default to 0."""
    payload = {
        "provider": "openai",
        "model": "gpt-4o",
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.01,
    }
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Analytics tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analytics_summary_includes_reasoning_tokens(client, auth_headers):
    """Analytics summary should include total_reasoning_tokens."""
    # Ingest an event with reasoning_tokens
    payload = {
        "provider": "openai",
        "model": "o1",
        "input_tokens": 100,
        "output_tokens": 50,
        "reasoning_tokens": 300,
        "total_tokens": 450,
        "cost_usd": 0.05,
    }
    await client.post("/v1/events", json=payload, headers=auth_headers)

    # Fetch analytics summary
    response = await client.get("/api/analytics/summary?period=30d", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_reasoning_tokens" in data
    assert data["total_reasoning_tokens"] >= 300
