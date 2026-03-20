# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.client module."""
import os
import pytest
from unittest.mock import MagicMock, patch


def make_mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    client.__class__.__module__ = "openai"
    return client


def make_mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    client.__class__.__module__ = "anthropic"
    return client


def test_wrap_returns_same_client():
    """wrap() returns the same client object (mutates it in place)."""
    import tokenbudget
    client = make_mock_openai_client()
    result = tokenbudget.wrap(client, api_key="test-key")
    assert result is client


def test_wrap_openai_client():
    """wrap() successfully wraps an OpenAI client."""
    import tokenbudget
    client = make_mock_openai_client()
    result = tokenbudget.wrap(client, api_key="test-key")
    assert result is client


def test_wrap_anthropic_client():
    """wrap() successfully wraps an Anthropic client."""
    import tokenbudget
    client = make_mock_anthropic_client()
    result = tokenbudget.wrap(client, api_key="test-key")
    assert result is client


def test_wrap_without_key_raises():
    """wrap() raises ValueError if no api_key is provided and env var not set."""
    import tokenbudget
    client = make_mock_openai_client()
    env = {k: v for k, v in os.environ.items() if k != "TOKENBUDGET_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError):
            tokenbudget.wrap(client)


def test_wrap_uses_env_var_for_api_key():
    """wrap() uses TOKENBUDGET_API_KEY env var when no api_key kwarg provided."""
    import tokenbudget
    client = make_mock_openai_client()
    with patch.dict(os.environ, {"TOKENBUDGET_API_KEY": "env-key"}):
        result = tokenbudget.wrap(client)
        assert result is client


def test_wrap_unknown_client_raises():
    """wrap() raises ValueError for unknown client types."""
    import tokenbudget
    client = MagicMock()
    client.__class__.__module__ = "some_unknown_library"
    with pytest.raises(ValueError):
        tokenbudget.wrap(client, api_key="test-key")


def test_wrap_patches_create_method():
    """wrap() patches the underlying create method."""
    import tokenbudget
    client = make_mock_openai_client()
    original_create = client.chat.completions.create
    tokenbudget.wrap(client, api_key="test-key")
    assert client.chat.completions.create != original_create


def test_shutdown_does_not_raise():
    """shutdown() can be called without raising."""
    import tokenbudget
    client = make_mock_openai_client()
    tokenbudget.wrap(client, api_key="test-key")
    # Should not raise
    tokenbudget.shutdown()


def test_wrap_with_custom_endpoint():
    """wrap() accepts a custom endpoint."""
    import tokenbudget
    client = make_mock_openai_client()
    result = tokenbudget.wrap(client, api_key="test-key", endpoint="https://custom.example.com")
    assert result is client
