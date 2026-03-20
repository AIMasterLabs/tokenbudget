# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.config module."""
import os
import pytest
from unittest.mock import patch


def test_config_from_kwargs():
    """Config loads api_key from keyword argument."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key-123")
    assert config.api_key == "test-key-123"


def test_config_from_env_var():
    """Config loads api_key from TOKENBUDGET_API_KEY env var."""
    from tokenbudget.config import TokenBudgetConfig
    with patch.dict(os.environ, {"TOKENBUDGET_API_KEY": "env-key-456"}):
        config = TokenBudgetConfig()
        assert config.api_key == "env-key-456"


def test_config_kwarg_takes_precedence_over_env():
    """Kwarg api_key takes precedence over env var."""
    from tokenbudget.config import TokenBudgetConfig
    with patch.dict(os.environ, {"TOKENBUDGET_API_KEY": "env-key"}):
        config = TokenBudgetConfig(api_key="kwarg-key")
        assert config.api_key == "kwarg-key"


def test_config_default_endpoint():
    """Config default endpoint is https://api.tokenbudget.com."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key")
    assert config.endpoint == "https://api.tokenbudget.com"


def test_config_custom_endpoint():
    """Config accepts a custom endpoint."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key", endpoint="https://custom.example.com")
    assert config.endpoint == "https://custom.example.com"


def test_config_missing_key_raises():
    """Config raises ValueError when no api_key is provided."""
    from tokenbudget.config import TokenBudgetConfig
    with patch.dict(os.environ, {}, clear=True):
        # Remove TOKENBUDGET_API_KEY if it exists
        env = {k: v for k, v in os.environ.items() if k != "TOKENBUDGET_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="api_key"):
                TokenBudgetConfig()


def test_config_default_enabled():
    """Config is enabled by default."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key")
    assert config.enabled is True


def test_config_default_flush_interval():
    """Config default flush_interval is 1.0 seconds."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key")
    assert config.flush_interval == 1.0


def test_config_default_max_queue_size():
    """Config default max_queue_size is 1000."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(api_key="test-key")
    assert config.max_queue_size == 1000


def test_config_custom_settings():
    """Config accepts custom settings."""
    from tokenbudget.config import TokenBudgetConfig
    config = TokenBudgetConfig(
        api_key="test-key",
        enabled=False,
        flush_interval=5.0,
        max_queue_size=500,
    )
    assert config.enabled is False
    assert config.flush_interval == 5.0
    assert config.max_queue_size == 500
