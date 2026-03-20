# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.providers.openai module."""
import pytest
from unittest.mock import MagicMock, patch, call


def make_openai_response(model="gpt-4o", prompt_tokens=100, completion_tokens=50):
    """Create a mock OpenAI chat completion response."""
    response = MagicMock()
    response.model = model
    response.usage = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens
    return response


def make_mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.__class__.__module__ = "openai"
    client.__module__ = "openai"
    return client


def test_openai_provider_detect():
    """OpenAI provider detects openai clients."""
    from tokenbudget.providers.openai import OpenAIProvider
    provider = OpenAIProvider()
    client = make_mock_openai_client()
    assert provider.detect(client) is True


def test_openai_provider_does_not_detect_anthropic():
    """OpenAI provider does not detect non-openai clients."""
    from tokenbudget.providers.openai import OpenAIProvider
    provider = OpenAIProvider()
    client = MagicMock()
    client.__class__.__module__ = "anthropic"
    assert provider.detect(client) is False


def test_extract_event_from_openai_response():
    """extract_event reads tokens from OpenAI response."""
    from tokenbudget.providers.openai import OpenAIProvider
    provider = OpenAIProvider()
    response = make_openai_response(model="gpt-4o", prompt_tokens=100, completion_tokens=50)
    event = provider.extract_event(response, latency_ms=300)
    assert event.provider == "openai"
    assert event.model == "gpt-4o"
    assert event.input_tokens == 100
    assert event.output_tokens == 50
    assert event.total_tokens == 150
    assert event.latency_ms == 300
    assert event.cost_usd >= 0.0


def test_extract_event_calculates_cost():
    """extract_event calculates cost for known models."""
    from tokenbudget.providers.openai import OpenAIProvider
    provider = OpenAIProvider()
    response = make_openai_response(model="gpt-4o", prompt_tokens=1000, completion_tokens=500)
    event = provider.extract_event(response, latency_ms=100)
    assert event.cost_usd > 0.0


def test_patch_wraps_create_method():
    """patch() monkey-patches client.chat.completions.create."""
    from tokenbudget.providers.openai import OpenAIProvider
    from tokenbudget.transport import EventTransport
    from tokenbudget.config import TokenBudgetConfig

    provider = OpenAIProvider()
    config = TokenBudgetConfig(api_key="test-key")
    transport = EventTransport(config)

    client = make_mock_openai_client()
    original_create = client.chat.completions.create

    provider.patch(client, transport)

    # The create method should be replaced
    assert client.chat.completions.create != original_create
    transport.shutdown()


def test_patch_calls_transport_send():
    """patch() causes transport.send to be called after create()."""
    from tokenbudget.providers.openai import OpenAIProvider
    from tokenbudget.transport import EventTransport
    from tokenbudget.config import TokenBudgetConfig

    provider = OpenAIProvider()
    config = TokenBudgetConfig(api_key="test-key")
    transport = MagicMock()

    client = make_mock_openai_client()
    response = make_openai_response()
    client.chat.completions.create.return_value = response

    provider.patch(client, transport)
    result = client.chat.completions.create(model="gpt-4o", messages=[])

    assert result == response
    transport.send.assert_called_once()


def test_patch_never_breaks_user_code():
    """patch() wraps create in try/except so exceptions in tracking don't break user code."""
    from tokenbudget.providers.openai import OpenAIProvider

    provider = OpenAIProvider()
    transport = MagicMock()
    transport.send.side_effect = RuntimeError("Transport error")

    client = make_mock_openai_client()
    response = make_openai_response()
    client.chat.completions.create.return_value = response

    provider.patch(client, transport)
    # Should NOT raise even though transport.send raises
    result = client.chat.completions.create(model="gpt-4o", messages=[])
    assert result == response


def test_patch_propagates_original_exception():
    """patch() propagates exceptions from the original create() call."""
    from tokenbudget.providers.openai import OpenAIProvider

    provider = OpenAIProvider()
    transport = MagicMock()

    client = make_mock_openai_client()
    client.chat.completions.create.side_effect = Exception("API error")

    provider.patch(client, transport)
    with pytest.raises(Exception, match="API error"):
        client.chat.completions.create(model="gpt-4o", messages=[])


def test_patch_includes_context_tags():
    """patch() includes current context tags in the event."""
    from tokenbudget.providers.openai import OpenAIProvider
    from tokenbudget.context import tags

    provider = OpenAIProvider()
    transport = MagicMock()

    client = make_mock_openai_client()
    response = make_openai_response()
    client.chat.completions.create.return_value = response

    provider.patch(client, transport)

    with tags(env="test", team="ml"):
        client.chat.completions.create(model="gpt-4o", messages=[])

    event = transport.send.call_args[0][0]
    assert event.tags.get("env") == "test"
    assert event.tags.get("team") == "ml"
