# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the public pricing endpoint.
"""
import pytest


@pytest.mark.asyncio
async def test_pricing_returns_200(client):
    response = await client.get("/v1/pricing")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_pricing_has_models_key(client):
    response = await client.get("/v1/pricing")
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], dict)


@pytest.mark.asyncio
async def test_pricing_has_gpt4_entry(client):
    response = await client.get("/v1/pricing")
    data = response.json()
    assert "gpt-4" in data["models"]
    gpt4 = data["models"]["gpt-4"]
    assert "input_per_1k" in gpt4
    assert "output_per_1k" in gpt4
    assert abs(gpt4["input_per_1k"] - 0.03) < 0.0001
    assert abs(gpt4["output_per_1k"] - 0.06) < 0.0001


@pytest.mark.asyncio
async def test_pricing_has_all_expected_models(client):
    expected_models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-haiku-4-5-20251001",
    ]
    response = await client.get("/v1/pricing")
    data = response.json()
    for model in expected_models:
        assert model in data["models"], f"Missing model: {model}"


@pytest.mark.asyncio
async def test_pricing_has_updated_at(client):
    response = await client.get("/v1/pricing")
    data = response.json()
    assert "updated_at" in data
    assert "2026" in data["updated_at"]


@pytest.mark.asyncio
async def test_pricing_is_public_no_auth_needed(client):
    """Pricing endpoint must NOT require authentication."""
    # No auth headers
    response = await client.get("/v1/pricing")
    assert response.status_code == 200
