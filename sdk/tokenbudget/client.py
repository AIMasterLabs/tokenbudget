# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget public client API."""
from __future__ import annotations

from typing import Any

from tokenbudget.config import TokenBudgetConfig
from tokenbudget.transport import EventTransport
from tokenbudget.providers import detect_provider

# Module-level singleton transport
_transport: EventTransport | None = None


def wrap(
    client: Any,
    api_key: str = "",
    endpoint: str = "",
    **kwargs: Any,
) -> Any:
    """Wrap an OpenAI or Anthropic client to track token usage.

    Patches the client in-place and returns the same object.

    Args:
        client: An OpenAI or Anthropic client instance.
        api_key: TokenBudget API key. Falls back to TOKENBUDGET_API_KEY env var.
        endpoint: Optional custom API endpoint.
        **kwargs: Additional config options (enabled, flush_interval, max_queue_size).

    Returns:
        The same client object, now patched to track usage.
    """
    global _transport

    config = TokenBudgetConfig(api_key=api_key, endpoint=endpoint, **kwargs)
    provider = detect_provider(client)

    if _transport is None or _transport._stop_event.is_set():
        _transport = EventTransport(config)

    provider.patch(client, _transport)
    return client


def shutdown() -> None:
    """Flush remaining events and close the transport."""
    global _transport
    if _transport is not None:
        _transport.shutdown()
        _transport = None
