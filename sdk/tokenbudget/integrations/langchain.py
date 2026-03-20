# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""LangChain callback handler for TokenBudget cost tracking.

Usage::

    from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

    handler = TokenBudgetCallbackHandler(api_key="tb_ak_...")
    llm = ChatOpenAI(callbacks=[handler])

Requires: ``pip install tokenbudget[langchain]``
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from tokenbudget.config import TokenBudgetConfig
from tokenbudget.pricing import calculate_cost
from tokenbudget.transport import EventTransport
from tokenbudget.types import UsageEvent

logger = logging.getLogger(__name__)


def _check_langchain() -> None:
    """Verify langchain-core is importable, raise helpful error if not."""
    try:
        import langchain_core  # noqa: F401
    except ImportError:
        raise ImportError(
            "langchain-core is required for the LangChain integration. "
            "Install it with: pip install tokenbudget[langchain]"
        )


def _get_base_class() -> type:
    """Return BaseCallbackHandler from langchain_core, or a plain fallback."""
    try:
        from langchain_core.callbacks import BaseCallbackHandler
        return BaseCallbackHandler
    except Exception:
        return object


# Build the class with the real base when langchain is available.
# We use a factory so the import is lazy.
__base = _get_base_class()


class TokenBudgetCallbackHandler(__base):
    """LangChain callback handler that tracks token usage via TokenBudget.

    Implements the LangChain ``BaseCallbackHandler`` interface.  When
    ``langchain-core`` is installed the class inherits from it directly;
    otherwise it inherits from ``object`` (useful for testing with mocks).
    """

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        tags: Optional[Dict[str, str]] = None,
        **config_kwargs: Any,
    ) -> None:
        _check_langchain()
        try:
            from langchain_core.callbacks import BaseCallbackHandler
            BaseCallbackHandler.__init__(self)
        except Exception:
            pass

        self._config = TokenBudgetConfig(api_key=api_key, endpoint=endpoint, **config_kwargs)
        self._transport = EventTransport(self._config)
        self._tags = tags or {}
        self._run_start_times: Dict[UUID, float] = {}

    # ------------------------------------------------------------------
    # LangChain callback interface
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record start time for latency calculation."""
        self._run_start_times[run_id] = time.time()

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Capture token usage from the LLM response and send to TokenBudget."""
        start_time = self._run_start_times.pop(run_id, None)
        latency_ms = int((time.time() - start_time) * 1000) if start_time else 0

        # Extract token usage from response
        llm_output = getattr(response, "llm_output", None) or {}
        token_usage = llm_output.get("token_usage", {})

        input_tokens = token_usage.get("prompt_tokens", 0)
        output_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", input_tokens + output_tokens)

        # Try to determine model name
        model = llm_output.get("model_name", "") or llm_output.get("model", "unknown")

        # Determine provider from model name heuristic
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
            tags={**self._tags, "source": "langchain"},
            metadata={},
        )
        self._transport.send(event)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Clean up start time on error."""
        self._run_start_times.pop(run_id, None)

    # Required no-op methods for BaseCallbackHandler
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        pass

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        pass

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        pass

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        pass

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        pass

    def on_text(self, text: str, **kwargs: Any) -> None:
        pass

    def shutdown(self) -> None:
        """Flush remaining events and close the transport."""
        self._transport.shutdown()
