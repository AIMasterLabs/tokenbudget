# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import pytest


@pytest.mark.asyncio
async def test_create_key_has_prefix(client, auth_headers):
    response = await client.post("/api/keys", json={"name": "My Key"}, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "raw_key" in data
    assert data["raw_key"].startswith("tb_ak_")
    assert data["key_prefix"].startswith("tb_ak_")
    assert data["is_active"] is True
    assert data["name"] == "My Key"


@pytest.mark.asyncio
async def test_list_keys(client, auth_headers):
    response = await client.get("/api/keys", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_delete_key(client, auth_headers, test_user_and_key, db_session):
    # Create a second API key for the authenticated user directly (avoiding the
    # _get_or_create_test_user logic which uses a separate test user)
    from app.services.key_service import create_api_key

    new_key, _ = await create_api_key(db_session, test_user_and_key["user_id"], "Key to delete")
    key_id = str(new_key.id)

    delete_resp = await client.delete(f"/api/keys/{key_id}", headers=auth_headers)
    assert delete_resp.status_code == 204
