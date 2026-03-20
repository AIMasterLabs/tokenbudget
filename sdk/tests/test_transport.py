# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.transport module."""
import time
import pytest
import httpx
from pytest_httpx import HTTPXMock


def make_event():
    from tokenbudget.types import UsageEvent
    return UsageEvent(
        provider="openai",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=0.003,
        latency_ms=250,
        tags={"env": "test"},
        metadata={},
    )


def make_config(endpoint="https://api.tokenbudget.com"):
    from tokenbudget.config import TokenBudgetConfig
    return TokenBudgetConfig(api_key="test-key", endpoint=endpoint, flush_interval=60.0)


def test_event_is_queued():
    """send() enqueues the event without blocking."""
    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    assert transport.queue.qsize() == 1
    transport.shutdown()


def test_flush_posts_to_endpoint(httpx_mock: HTTPXMock):
    """flush_sync() POSTs events to /v1/events/batch."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.tokenbudget.com/v1/events/batch",
        status_code=200,
        json={"ok": True},
    )
    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    transport.flush_sync()
    # Queue should be empty after successful flush
    assert transport.queue.qsize() == 0


def test_flush_serializes_event(httpx_mock: HTTPXMock):
    """flush_sync() sends correct JSON structure."""
    captured = {}

    def capture_request(request: httpx.Request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    httpx_mock.add_callback(capture_request, url="https://api.tokenbudget.com/v1/events/batch")

    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    transport.flush_sync()

    assert "events" in captured["body"]
    assert len(captured["body"]["events"]) == 1
    evt = captured["body"]["events"][0]
    assert evt["provider"] == "openai"
    assert evt["model"] == "gpt-4o"
    assert evt["input_tokens"] == 100
    assert evt["output_tokens"] == 50
    assert evt["total_tokens"] == 150
    assert evt["cost_usd"] == pytest.approx(0.003)
    assert evt["latency_ms"] == 250


def test_flush_requeues_on_http_error(httpx_mock: HTTPXMock):
    """On HTTP error, events are re-queued for retry."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.tokenbudget.com/v1/events/batch",
        status_code=500,
    )
    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    transport.flush_sync()
    # Event should be re-queued after failure
    assert transport.queue.qsize() == 1


def test_flush_requeues_on_network_failure(httpx_mock: HTTPXMock):
    """On network failure, events are re-queued for retry."""
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url="https://api.tokenbudget.com/v1/events/batch",
    )
    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    transport.flush_sync()
    # Event should be re-queued after network failure
    assert transport.queue.qsize() == 1


def test_send_never_raises():
    """send() never raises even with bad config."""
    from tokenbudget.transport import EventTransport
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key", endpoint="https://invalid.example.xyz")
    transport = EventTransport(config)
    event = make_event()
    # Should not raise
    transport.send(event)
    transport.shutdown()


def test_shutdown_flushes_remaining(httpx_mock: HTTPXMock):
    """shutdown() flushes remaining events before closing."""
    httpx_mock.add_response(
        method="POST",
        url="https://api.tokenbudget.com/v1/events/batch",
        status_code=200,
        json={"ok": True},
    )
    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)
    event = make_event()
    transport.send(event)
    transport.shutdown()
    assert transport.queue.qsize() == 0


def test_multiple_events_batched(httpx_mock: HTTPXMock):
    """Multiple events are sent in a single batch."""
    captured = {}

    def capture_request(request: httpx.Request):
        import json
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    httpx_mock.add_callback(capture_request, url="https://api.tokenbudget.com/v1/events/batch")

    from tokenbudget.transport import EventTransport
    config = make_config()
    transport = EventTransport(config)

    for _ in range(3):
        transport.send(make_event())

    transport.flush_sync()
    assert len(captured["body"]["events"]) == 3
