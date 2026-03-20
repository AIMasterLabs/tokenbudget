# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for the OpenTelemetry OTLP trace ingest endpoint."""
import pytest
from httpx import AsyncClient


def _make_otlp_trace(spans: list[dict]) -> dict:
    """Build a minimal OTLP ExportTraceServiceRequest JSON payload."""
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "scope": {"name": "test"},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def _make_genai_span(
    *,
    system: str = "openai",
    model: str = "gpt-4o",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cost: float | None = None,
    name: str = "chat",
    start_ns: str = "1000000000",
    end_ns: str = "2000000000",
) -> dict:
    """Build a single GenAI span with OTel semantic convention attributes."""
    attrs = [
        {"key": "gen_ai.system", "value": {"stringValue": system}},
        {"key": "gen_ai.request.model", "value": {"stringValue": model}},
        {"key": "gen_ai.usage.input_tokens", "value": {"intValue": str(input_tokens)}},
        {"key": "gen_ai.usage.output_tokens", "value": {"intValue": str(output_tokens)}},
    ]
    if cost is not None:
        attrs.append({"key": "gen_ai.usage.cost", "value": {"doubleValue": cost}})
    return {
        "traceId": "abc123",
        "spanId": "def456",
        "name": name,
        "startTimeUnixNano": start_ns,
        "endTimeUnixNano": end_ns,
        "attributes": attrs,
    }


def _make_non_genai_span() -> dict:
    """Build a span without any GenAI attributes."""
    return {
        "traceId": "abc123",
        "spanId": "ghi789",
        "name": "http.request",
        "startTimeUnixNano": "1000000000",
        "endTimeUnixNano": "1500000000",
        "attributes": [
            {"key": "http.method", "value": {"stringValue": "GET"}},
            {"key": "http.url", "value": {"stringValue": "https://example.com"}},
        ],
    }


@pytest.mark.asyncio
async def test_valid_otel_trace_creates_events(client: AsyncClient, test_user_and_key):
    """Valid OTel JSON trace with GenAI span should be accepted and persisted."""
    span = _make_genai_span(model="gpt-4o", input_tokens=200, output_tokens=100)
    payload = _make_otlp_trace([span])

    resp = await client.post(
        "/v1/traces",
        json=payload,
        headers={"X-TokenBudget-Key": test_user_and_key["raw_key"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["persisted"] is True


@pytest.mark.asyncio
async def test_missing_auth_header_still_accepts(client: AsyncClient):
    """Missing auth header should still accept (never break customer)."""
    span = _make_genai_span()
    payload = _make_otlp_trace([span])

    resp = await client.post("/v1/traces", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 1
    assert data["persisted"] is False


@pytest.mark.asyncio
async def test_non_genai_spans_ignored(client: AsyncClient, test_user_and_key):
    """Non-GenAI spans should be ignored gracefully."""
    span = _make_non_genai_span()
    payload = _make_otlp_trace([span])

    resp = await client.post(
        "/v1/traces",
        json=payload,
        headers={"X-TokenBudget-Key": test_user_and_key["raw_key"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 0


@pytest.mark.asyncio
async def test_multiple_spans_multiple_events(client: AsyncClient, test_user_and_key):
    """Multiple GenAI spans in one trace should create multiple events."""
    spans = [
        _make_genai_span(system="openai", model="gpt-4o", input_tokens=100, output_tokens=50),
        _make_genai_span(system="anthropic", model="claude-sonnet-4", input_tokens=200, output_tokens=100),
        _make_non_genai_span(),  # should be ignored
    ]
    payload = _make_otlp_trace(spans)

    resp = await client.post(
        "/v1/traces",
        json=payload,
        headers={"X-TokenBudget-Key": test_user_and_key["raw_key"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["accepted"] == 2
    assert data["persisted"] is True


@pytest.mark.asyncio
async def test_explicit_cost_used(client: AsyncClient, test_user_and_key):
    """When gen_ai.usage.cost is provided, it should be used instead of calculated cost."""
    span = _make_genai_span(cost=0.042, model="gpt-4o", input_tokens=100, output_tokens=50)
    payload = _make_otlp_trace([span])

    resp = await client.post(
        "/v1/traces",
        json=payload,
        headers={"X-TokenBudget-Key": test_user_and_key["raw_key"]},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1


@pytest.mark.asyncio
async def test_empty_trace_body(client: AsyncClient):
    """Empty resourceSpans should return accepted=0."""
    resp = await client.post("/v1/traces", json={"resourceSpans": []})
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 0


@pytest.mark.asyncio
async def test_latency_calculated_from_timestamps(client: AsyncClient, test_user_and_key):
    """Latency should be calculated from span start/end timestamps."""
    # 1 second = 1_000_000_000 nanoseconds = 1000 ms
    span = _make_genai_span(start_ns="1000000000", end_ns="2000000000")
    payload = _make_otlp_trace([span])

    resp = await client.post(
        "/v1/traces",
        json=payload,
        headers={"X-TokenBudget-Key": test_user_and_key["raw_key"]},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] == 1
