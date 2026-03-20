# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import pytest


@pytest.mark.asyncio
async def test_join_waitlist_returns_200(client):
    response = await client.post(
        "/api/waitlist",
        json={"email": "newuser@example.com", "source": "landing"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "list" in data["message"].lower()


@pytest.mark.asyncio
async def test_join_waitlist_duplicate_returns_already_on_list(client):
    email = "duplicate@example.com"
    await client.post("/api/waitlist", json={"email": email})
    response = await client.post("/api/waitlist", json={"email": email})
    assert response.status_code == 200
    data = response.json()
    assert "already" in data["message"].lower()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_list_waitlist_without_admin_key_returns_error(client):
    response = await client.get("/api/waitlist")
    # 422 when header is missing (FastAPI validation), or 403 when wrong key
    assert response.status_code in (403, 422)
