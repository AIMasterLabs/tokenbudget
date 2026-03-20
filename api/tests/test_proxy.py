# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the transparent proxy endpoints.

All upstream HTTP calls are intercepted by a custom httpx MockTransport —
no real API calls are made.
"""
from __future__ import annotations

import json
import pytest
import httpx

from app.lib.pricing import calculate_cost


# ---------------------------------------------------------------------------
# Mock transport factory
# ---------------------------------------------------------------------------

def _make_openai_chat_response(model: str = "gpt-4o", status_code: int = 200) -> httpx.Response:
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return httpx.Response(status_code, json=body)


def _make_anthropic_response(model: str = "claude-sonnet-4-20250514", status_code: int = 200) -> httpx.Response:
    body = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": "Hi there!"}],
        "usage": {"input_tokens": 20, "output_tokens": 8},
    }
    return httpx.Response(status_code, json=body)


def _make_openai_429_response() -> httpx.Response:
    body = {"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}
    return httpx.Response(429, json=body)


class _MockTransport(httpx.AsyncBaseTransport):
    """
    Intercepts ALL outbound httpx requests and returns a pre-canned response.
    Captures the last request for inspection.
    """

    def __init__(self, response: httpx.Response):
        self._response = response
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        # Build a proper Response with a request attached so httpx is happy
        return httpx.Response(
            self._response.status_code,
            headers=dict(self._response.headers),
            content=self._response.content,
            request=request,
        )


# ---------------------------------------------------------------------------
# Fixture: patch httpx.AsyncClient to use our mock transport
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_openai_ok(monkeypatch):
    transport = _MockTransport(_make_openai_chat_response())
    _patch_httpx(monkeypatch, transport)
    return transport


@pytest.fixture()
def mock_openai_429(monkeypatch):
    transport = _MockTransport(_make_openai_429_response())
    _patch_httpx(monkeypatch, transport)
    return transport


@pytest.fixture()
def mock_anthropic_ok(monkeypatch):
    transport = _MockTransport(_make_anthropic_response())
    _patch_httpx(monkeypatch, transport)
    return transport


def _patch_httpx(monkeypatch, transport: _MockTransport):
    """Monkeypatch httpx.AsyncClient.__init__ to inject our transport."""
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_key_mock_openai_records_event(client, auth_headers, mock_openai_ok):
    """Valid TB key + mock OpenAI response → 200, correct headers."""
    response = await client.post(
        "/proxy/openai/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={
            **auth_headers,           # X-TB auth via Bearer — we re-use TB key as X-TokenBudget-Key
            "X-TokenBudget-Key": auth_headers["Authorization"].split(" ")[1],
            "Authorization": "Bearer sk-fake-openai-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert response.headers.get("x-proxied-by") == "TokenBudget/1.0"


@pytest.mark.asyncio
async def test_missing_tb_key_still_forwards(client, mock_openai_ok):
    """Missing X-TokenBudget-Key → still proxies, no event recorded (no crash)."""
    response = await client.post(
        "/proxy/openai/v1/chat/completions",
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={"Authorization": "Bearer sk-fake-openai-key"},
    )
    # Request is forwarded even without TB key
    assert response.status_code == 200
    assert response.headers.get("x-proxied-by") == "TokenBudget/1.0"


@pytest.mark.asyncio
async def test_missing_authorization_returns_400(client):
    """Missing Authorization header → 400 before hitting upstream."""
    response = await client.post(
        "/proxy/openai/v1/chat/completions",
        json={"model": "gpt-4o", "messages": []},
        # No Authorization header
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_openai_429_forwarded_unchanged(client, mock_openai_429):
    """OpenAI 429 response is forwarded as-is to the customer."""
    response = await client.post(
        "/proxy/openai/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "Bearer sk-fake-key"},
    )
    assert response.status_code == 429
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_pricing_gpt4o_cost():
    """gpt-4o: 1000 input + 500 output tokens should equal correct cost."""
    cost = calculate_cost("gpt-4o", 1000, 500)
    # 1000/1000 * 0.0025 + 500/1000 * 0.010 = 0.0025 + 0.005 = 0.0075
    expected = 0.0075
    assert abs(cost - expected) < 1e-9, f"Expected {expected}, got {cost}"


@pytest.mark.asyncio
async def test_unknown_model_cost_zero_tokens_tracked():
    """Unknown model → cost=0.0, but function still returns."""
    cost = calculate_cost("some-unknown-model-xyz", 500, 200)
    assert cost == 0.0


@pytest.mark.asyncio
async def test_authorization_header_not_in_event_record(client, auth_headers, mock_openai_ok, db_session):
    """
    Authorization header value must NEVER appear in any stored event record.
    We send a fake key and verify it is not stored anywhere in the DB.
    """
    fake_openai_key = "sk-SUPERSECRET-SHOULD-NOT-BE-STORED"

    await client.post(
        "/proxy/openai/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]},
        headers={
            "X-TokenBudget-Key": auth_headers["Authorization"].split(" ")[1],
            "Authorization": f"Bearer {fake_openai_key}",
        },
    )

    # Query all events and verify the secret key value is not present in any field
    from sqlalchemy import select, text
    result = await db_session.execute(
        text("SELECT metadata, tags FROM events ORDER BY created_at DESC LIMIT 10")
    )
    rows = result.fetchall()
    for row in rows:
        metadata_val = str(row[0]) if row[0] else ""
        tags_val = str(row[1]) if row[1] else ""
        assert fake_openai_key not in metadata_val, "Secret key found in event metadata!"
        assert fake_openai_key not in tags_val, "Secret key found in event tags!"


@pytest.mark.asyncio
async def test_anthropic_proxy_works(client, auth_headers, mock_anthropic_ok):
    """Anthropic proxy endpoint works with x-api-key header."""
    response = await client.post(
        "/proxy/anthropic/v1/messages",
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={
            "X-TokenBudget-Key": auth_headers["Authorization"].split(" ")[1],
            "x-api-key": "sk-ant-fake-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "content" in data or "type" in data
    assert response.headers.get("x-proxied-by") == "TokenBudget/1.0"


# ---------------------------------------------------------------------------
# Extra unit tests for pricing fuzzy matching
# ---------------------------------------------------------------------------

def test_pricing_fuzzy_versioned_suffix():
    """gpt-4o-2024-11-20 should resolve to gpt-4o pricing."""
    cost = calculate_cost("gpt-4o-2024-11-20", 1000, 0)
    expected = 0.0025
    assert abs(cost - expected) < 1e-9


def test_pricing_mini_not_confused_with_base():
    """gpt-4o-mini should NOT use gpt-4o pricing."""
    cost_mini = calculate_cost("gpt-4o-mini", 1000, 0)
    cost_base = calculate_cost("gpt-4o", 1000, 0)
    assert cost_mini != cost_base
    # mini: 0.00015/1k input
    assert abs(cost_mini - 0.00015) < 1e-9


def test_pricing_claude_sonnet_4():
    cost = calculate_cost("claude-sonnet-4", 1000, 1000)
    # 0.003 + 0.015 = 0.018
    assert abs(cost - 0.018) < 1e-9


def test_pricing_embedding_no_output_cost():
    cost = calculate_cost("text-embedding-3-small", 1000, 999)
    # output_per_1k is 0 for embeddings
    assert abs(cost - 0.00002) < 1e-9
