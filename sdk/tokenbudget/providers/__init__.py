# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget provider registry."""
from __future__ import annotations

from typing import Any

from tokenbudget.providers.base import BaseProvider
from tokenbudget.providers.openai import OpenAIProvider
from tokenbudget.providers.anthropic import AnthropicProvider
from tokenbudget.providers.bedrock import BedrockProvider, wrap_bedrock

PROVIDERS: list[BaseProvider] = [
    OpenAIProvider(),
    AnthropicProvider(),
    BedrockProvider(),
]


def detect_provider(client: Any) -> BaseProvider:
    """Return the matching provider for the given client.

    Raises ValueError if no provider matches.
    """
    for provider in PROVIDERS:
        if provider.detect(client):
            return provider
    raise ValueError(
        f"No TokenBudget provider found for client of type "
        f"{type(client).__module__}.{type(client).__name__}. "
        f"Supported providers: openai, anthropic, bedrock."
    )

__all__ = ["detect_provider", "wrap_bedrock", "PROVIDERS"]
