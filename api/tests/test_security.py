# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Security tests: input validation and key rotation."""

import pytest


# ---------------------------------------------------------------------------
# Base valid event payload
# ---------------------------------------------------------------------------

VALID_EVENT = {
    "provider": "openai",
    "model": "gpt-4o",
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "cost_usd": 0.003,
    "latency_ms": 800,
}


# ---------------------------------------------------------------------------
# Input validation — event fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_cost_usd_too_high_returns_422(client, auth_headers):
    """cost_usd above MAX_COST_USD (100.0) must be rejected with 422."""
    payload = {**VALID_EVENT, "cost_usd": 200.0}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_input_tokens_too_large_returns_422(client, auth_headers):
    """input_tokens above MAX_INPUT_TOKENS (2_000_000) must be rejected with 422."""
    payload = {**VALID_EVENT, "input_tokens": 3_000_000, "total_tokens": 3_000_050}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_output_tokens_too_large_returns_422(client, auth_headers):
    """output_tokens above MAX_OUTPUT_TOKENS (2_000_000) must be rejected with 422."""
    payload = {**VALID_EVENT, "output_tokens": 2_500_000, "total_tokens": 2_500_100}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_invalid_provider_returns_422(client, auth_headers):
    """A provider not in VALID_PROVIDERS must be rejected with 422."""
    payload = {**VALID_EVENT, "provider": "notavalidprovider"}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_negative_cost_usd_returns_422(client, auth_headers):
    """Negative cost_usd must be rejected with 422."""
    payload = {**VALID_EVENT, "cost_usd": -1.0}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_model_too_long_returns_422(client, auth_headers):
    """model name exceeding MAX_MODEL_LEN (100) chars must be rejected with 422."""
    payload = {**VALID_EVENT, "model": "x" * 101}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_latency_too_large_returns_422(client, auth_headers):
    """latency_ms above MAX_LATENCY_MS (300_000) must be rejected with 422."""
    payload = {**VALID_EVENT, "latency_ms": 400_000}
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_event_valid_boundary_values_accepted(client, auth_headers):
    """Events at the boundary of allowed limits should be accepted (202)."""
    payload = {
        "provider": "anthropic",
        "model": "claude-3",
        "input_tokens": 2_000_000,
        "output_tokens": 2_000_000,
        "total_tokens": 4_000_000,
        "cost_usd": 100.0,
        "latency_ms": 300_000,
    }
    response = await client.post("/v1/events", json=payload, headers=auth_headers)
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_key_rotation_creates_new_and_revokes_old(
    client, auth_headers, test_user_and_key, db_session
):
    """
    POST /api/keys/{id}/rotate must:
    - Return 201 with a new raw key
    - Revoke the original key (is_active becomes False)
    """
    from app.models.api_key import ApiKey
    from sqlalchemy import select

    old_key_id = str(test_user_and_key["api_key_id"])

    response = await client.post(f"/api/keys/{old_key_id}/rotate", headers=auth_headers)
    assert response.status_code == 201, response.text

    data = response.json()
    assert "raw_key" in data
    assert data["raw_key"].startswith("tb_ak_")
    assert data["id"] != old_key_id  # new key has a different id
    assert data["rotated_key_id"] == old_key_id
    assert data["is_active"] is True

    # Confirm old key is now inactive in DB
    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == test_user_and_key["api_key_id"])
    )
    old_key = result.scalar_one_or_none()
    assert old_key is not None
    assert old_key.is_active is False


@pytest.mark.asyncio
async def test_key_rotation_requires_auth(client, test_user_and_key):
    """Rotating a key without a valid auth header must return 401."""
    old_key_id = str(test_user_and_key["api_key_id"])
    response = await client.post(f"/api/keys/{old_key_id}/rotate")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_key_rotation_not_found_returns_404(client, auth_headers):
    """Rotating a non-existent key id must return 404."""
    import uuid

    fake_id = str(uuid.uuid4())
    response = await client.post(f"/api/keys/{fake_id}/rotate", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_last_used_at_updated_on_auth(client, auth_headers, test_user_and_key, db_session):
    """After a successful authenticated request, last_used_at should be set."""
    from app.models.api_key import ApiKey
    from sqlalchemy import select

    # Make an authenticated request
    response = await client.get("/api/keys", headers=auth_headers)
    assert response.status_code == 200

    # Expire the session cache so we get a fresh read
    await db_session.close()

    # Re-query the key
    result = await db_session.execute(
        select(ApiKey).where(ApiKey.id == test_user_and_key["api_key_id"])
    )
    key = result.scalar_one_or_none()
    assert key is not None
    assert key.last_used_at is not None
