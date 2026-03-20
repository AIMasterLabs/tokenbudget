# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import pytest

SAMPLE_EVENT = {
    "provider": "openai",
    "model": "gpt-4o",
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "cost_usd": 0.003,
    "latency_ms": 800,
}


@pytest.mark.asyncio
async def test_post_event_with_valid_key(client, auth_headers):
    response = await client.post("/v1/events", json=SAMPLE_EVENT, headers=auth_headers)
    assert response.status_code == 202
    assert response.json()["accepted"] is True


@pytest.mark.asyncio
async def test_post_event_without_key(client):
    response = await client.post("/v1/events", json=SAMPLE_EVENT)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_event_batch(client, auth_headers):
    batch = {"events": [SAMPLE_EVENT, SAMPLE_EVENT, SAMPLE_EVENT]}
    response = await client.post("/v1/events/batch", json=batch, headers=auth_headers)
    assert response.status_code == 202
    data = response.json()
    assert data["accepted"] is True
    assert data["count"] == 3


@pytest.mark.asyncio
async def test_post_event_invalid_payload(client, auth_headers):
    # Missing required fields
    response = await client.post(
        "/v1/events",
        json={"provider": "openai"},
        headers=auth_headers,
    )
    assert response.status_code == 422
