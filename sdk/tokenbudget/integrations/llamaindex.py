# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""LlamaIndex callback handler for TokenBudget cost tracking.

Usage::

    from tokenbudget.integrations.llamaindex import TokenBudgetHandler

    handler = TokenBudgetHandler(api_key="tb_ak_...")
    Settings.callback_manager.add_handler(handler)

Requires: ``pip install tokenbudget[llamaindex]``
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from tokenbudget.config import TokenBudgetConfig
from tokenbudget.pricing import calculate_cost
from tokenbudget.transport import EventTransport
from tokenbudget.types import UsageEvent

logger = logging.getLogger(__name__)


def _check_llamaindex() -> None:
    """Verify llama-index-core is importable, raise helpful error if not."""
    try:
        import llama_index.core  # noqa: F401
    except ImportError:
        raise ImportError(
            "llama-index-core is required for the LlamaIndex integration. "
            "Install it with: pip install tokenbudget[llamaindex]"
        )


def _get_base_class() -> type:
    """Return BaseCallbackHandler from llama_index.core, or a plain fallback."""
    try:
        from llama_index.core.callbacks.base_handler import BaseCallbackHandler
        return BaseCallbackHandler
    except Exception:
        return object


_CBEventType: Any = None


def _get_cb_event_type() -> Any:
    """Lazy accessor for CBEventType."""
    global _CBEventType
    if _CBEventType is None:
        from llama_index.core.callbacks.schema import CBEventType
        _CBEventType = CBEventType
    return _CBEventType


__base = _get_base_class()


class TokenBudgetHandler(__base):
    """LlamaIndex callback handler that tracks token usage via TokenBudget.

    Implements the LlamaIndex ``BaseCallbackHandler`` interface.  When
    ``llama-index-core`` is installed the class inherits from it directly;
    otherwise it inherits from ``object`` (useful for testing with mocks).
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        tags: Optional[Dict[str, str]] = None,
        **config_kwargs: Any,
    ) -> None:
        _check_llamaindex()
        try:
            from llama_index.core.callbacks.base_handler import BaseCallbackHandler
            from llama_index.core.callbacks.schema import CBEventType
            BaseCallbackHandler.__init__(
                self,
                event_starts_to_trace=[CBEventType.LLM],
                event_ends_to_trace=[CBEventType.LLM],
            )
        except Exception:
            pass

        self._config = TokenBudgetConfig(api_key=api_key, endpoint=endpoint, **config_kwargs)
        self._transport = EventTransport(self._config)
        self._tags = tags or {}
        self._event_start_times: Dict[str, float] = {}

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Called when a trace starts."""
        pass

    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Called when a trace ends."""
        pass

    def on_event_start(
        self,
        event_type: Any,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Record start time for LLM events."""
        CBEventType = _get_cb_event_type()

        if event_type == CBEventType.LLM:
            self._event_start_times[event_id] = time.time()
        return event_id

    def on_event_end(
        self,
        event_type: Any,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Capture token usage from LLM completion events."""
        CBEventType = _get_cb_event_type()

        if event_type != CBEventType.LLM:
            return

        start_time = self._event_start_times.pop(event_id, None)
        latency_ms = int((time.time() - start_time) * 1000) if start_time else 0

        payload = payload or {}

        # Extract token usage — LlamaIndex typically puts it in the response
        # under various keys depending on the LLM provider
        input_tokens = 0
        output_tokens = 0
        model = "unknown"

        # Try to get from response directly
        response = payload.get("response", None)
        if response is not None:
            raw = getattr(response, "raw", None) or {}
            if isinstance(raw, dict):
                usage = raw.get("usage", {})
                input_tokens = getattr(usage, "prompt_tokens", 0) or usage.get("prompt_tokens", 0)
                output_tokens = (
                    getattr(usage, "completion_tokens", 0) or usage.get("completion_tokens", 0)
                )
                model = raw.get("model", "unknown")
            elif hasattr(raw, "usage"):
                usage = raw.usage
                input_tokens = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0)
                output_tokens = (
                    getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0)
                )
                model = getattr(raw, "model", "unknown")

        # Fallback: check payload keys directly
        if input_tokens == 0:
            input_tokens = payload.get("prompt_tokens", 0)
            output_tokens = payload.get("completion_tokens", 0)

        total_tokens = input_tokens + output_tokens

        provider = "openai"
        if "claude" in model.lower():
            provider = "anthropic"

        cost_usd = calculate_cost(model, input_tokens, output_tokens)

        event = UsageEvent(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            tags={**self._tags, "source": "llamaindex"},
            metadata={},
        )
        self._transport.send(event)

    def shutdown(self) -> None:
        """Flush remaining events and close the transport."""
        self._transport.shutdown()
