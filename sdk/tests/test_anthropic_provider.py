# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.providers.anthropic module."""
import pytest
from unittest.mock import MagicMock, patch


def make_anthropic_response(model="claude-sonnet-4-20250514", input_tokens=100, output_tokens=50):
    """Create a mock Anthropic messages response."""
    response = MagicMock()
    response.model = model
    response.usage = MagicMock()
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def make_mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    client.__class__.__module__ = "anthropic"
    client.__module__ = "anthropic"
    return client


def test_anthropic_provider_detect():
    """Anthropic provider detects anthropic clients."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider()
    client = make_mock_anthropic_client()
    assert provider.detect(client) is True


def test_anthropic_provider_does_not_detect_openai():
    """Anthropic provider does not detect non-anthropic clients."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider()
    client = MagicMock()
    client.__class__.__module__ = "openai"
    assert provider.detect(client) is False


def test_extract_event_from_anthropic_response():
    """extract_event reads tokens from Anthropic response."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider()
    response = make_anthropic_response(
        model="claude-sonnet-4-20250514", input_tokens=100, output_tokens=50
    )
    event = provider.extract_event(response, latency_ms=400)
    assert event.provider == "anthropic"
    assert event.model == "claude-sonnet-4-20250514"
    assert event.input_tokens == 100
    assert event.output_tokens == 50
    assert event.total_tokens == 150
    assert event.latency_ms == 400
    assert event.cost_usd >= 0.0


def test_extract_event_calculates_cost():
    """extract_event calculates cost for known Claude models."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    provider = AnthropicProvider()
    response = make_anthropic_response(
        model="claude-sonnet-4-20250514", input_tokens=1000, output_tokens=500
    )
    event = provider.extract_event(response, latency_ms=100)
    assert event.cost_usd > 0.0


def test_patch_wraps_messages_create():
    """patch() monkey-patches client.messages.create."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    from tokenbudget.transport import EventTransport
    from tokenbudget.config import TokenBudgetConfig

    provider = AnthropicProvider()
    config = TokenBudgetConfig(api_key="test-key")
    transport = EventTransport(config)

    client = make_mock_anthropic_client()
    original_create = client.messages.create

    provider.patch(client, transport)

    assert client.messages.create != original_create
    transport.shutdown()


def test_patch_calls_transport_send():
    """patch() causes transport.send to be called after create()."""
    from tokenbudget.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    transport = MagicMock()

    client = make_mock_anthropic_client()
    response = make_anthropic_response()
    client.messages.create.return_value = response

    provider.patch(client, transport)
    result = client.messages.create(model="claude-sonnet-4-20250514", messages=[])

    assert result == response
    transport.send.assert_called_once()


def test_patch_never_breaks_user_code():
    """patch() wraps messages.create so tracking errors don't break user code."""
    from tokenbudget.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    transport = MagicMock()
    transport.send.side_effect = RuntimeError("Transport error")

    client = make_mock_anthropic_client()
    response = make_anthropic_response()
    client.messages.create.return_value = response

    provider.patch(client, transport)
    result = client.messages.create(model="claude-sonnet-4-20250514", messages=[])
    assert result == response


def test_patch_propagates_original_exception():
    """patch() propagates exceptions from the original messages.create() call."""
    from tokenbudget.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    transport = MagicMock()

    client = make_mock_anthropic_client()
    client.messages.create.side_effect = Exception("API error")

    provider.patch(client, transport)
    with pytest.raises(Exception, match="API error"):
        client.messages.create(model="claude-sonnet-4-20250514", messages=[])


def test_patch_includes_context_tags():
    """patch() includes current context tags in the event."""
    from tokenbudget.providers.anthropic import AnthropicProvider
    from tokenbudget.context import tags

    provider = AnthropicProvider()
    transport = MagicMock()

    client = make_mock_anthropic_client()
    response = make_anthropic_response()
    client.messages.create.return_value = response

    provider.patch(client, transport)

    with tags(env="test", team="ml"):
        client.messages.create(model="claude-sonnet-4-20250514", messages=[])

    event = transport.send.call_args[0][0]
    assert event.tags.get("env") == "test"
    assert event.tags.get("team") == "ml"
