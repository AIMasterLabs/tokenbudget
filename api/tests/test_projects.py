# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for project management endpoints.
"""
import pytest


PROJECT_PAYLOAD = {
    "name": "My Test Project",
    "description": "A project for testing",
    "color": "#ff5733",
}


@pytest.mark.asyncio
async def test_create_project(client, auth_headers):
    response = await client.post("/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Test Project"
    assert data["description"] == "A project for testing"
    assert data["color"] == "#ff5733"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    # Slug should be auto-generated from the name; may have a uniqueness suffix
    assert "slug" in data
    assert data["slug"].startswith("my-test-project")


@pytest.mark.asyncio
async def test_create_project_slug_generated(client, auth_headers):
    """Slug is derived from name: lowercased, spaces replaced with hyphens."""
    response = await client.post(
        "/api/projects",
        json={"name": "Hello World Project"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "hello-world-project"


@pytest.mark.asyncio
async def test_create_project_default_color(client, auth_headers):
    response = await client.post(
        "/api/projects",
        json={"name": "Minimal Project"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["color"] == "#6366f1"


@pytest.mark.asyncio
async def test_list_projects(client, auth_headers):
    # Create two projects
    await client.post("/api/projects", json={"name": "Alpha"}, headers=auth_headers)
    await client.post("/api/projects", json={"name": "Beta"}, headers=auth_headers)

    response = await client.get("/api/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_project_by_id(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "My Test Project"


@pytest.mark.asyncio
async def test_get_project_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/projects/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/projects/{project_id}",
        json={"name": "Updated Name", "color": "#000000"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["color"] == "#000000"


@pytest.mark.asyncio
async def test_update_project_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.put(
        f"/api/projects/{fake_id}",
        json={"name": "Nope"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"deleted": True}

    # Subsequent GET should 404
    get_resp = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_not_found(client, auth_headers):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.delete(f"/api/projects/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_projects_require_auth(client):
    response = await client.get("/api/projects")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_project_analytics_summary(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/projects/{project_id}/analytics/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_cost_usd" in data
    assert "total_requests" in data
    assert "total_input_tokens" in data
    assert "total_output_tokens" in data
    assert "avg_cost_per_request" in data
    assert "avg_latency_ms" in data


@pytest.mark.asyncio
async def test_project_analytics_timeseries(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/projects/{project_id}/analytics/timeseries",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_project_keys(client, auth_headers):
    create_resp = await client.post(
        "/api/projects", json=PROJECT_PAYLOAD, headers=auth_headers
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/projects/{project_id}/keys",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
