# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""OpenAI provider integration."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from tokenbudget.providers.base import BaseProvider
from tokenbudget.pricing import calculate_cost
from tokenbudget.types import UsageEvent

if TYPE_CHECKING:
    from tokenbudget.transport import EventTransport

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Provider integration for the OpenAI Python client."""

    def detect(self, client: Any) -> bool:
        """Return True if the client is from the openai package."""
        return type(client).__module__.startswith("openai")

    def extract_event(self, response: Any, latency_ms: int) -> UsageEvent:
        """Extract a UsageEvent from an OpenAI chat completion response."""
        from tokenbudget.context import get_current_tags

        model = getattr(response, "model", "unknown")
        usage = getattr(response, "usage", None)

        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        total_tokens = input_tokens + output_tokens

        cost = calculate_cost(model, input_tokens, output_tokens)
        tags = get_current_tags()

        return UsageEvent(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            tags=tags,
        )

    def patch(self, client: Any, transport: "EventTransport") -> None:
        """Monkey-patch client.chat.completions.create to track usage."""
        original_create = client.chat.completions.create

        def patched_create(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            response = original_create(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            try:
                event = self.extract_event(response, latency_ms=elapsed_ms)
                transport.send(event)
            except Exception as exc:
                logger.warning("TokenBudget: failed to track OpenAI event: %s", exc)
            return response

        client.chat.completions.create = patched_create
