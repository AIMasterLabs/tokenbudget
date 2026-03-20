# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.integrations (LangChain & LlamaIndex callback handlers)."""
from __future__ import annotations

import sys
import types
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers: build minimal mock modules for langchain-core and llama-index-core
# so we can test without installing those heavy dependencies.
# ---------------------------------------------------------------------------


def _install_fake_langchain():
    """Inject a minimal langchain_core mock into sys.modules."""
    if "langchain_core" in sys.modules:
        return

    class _BaseCallbackHandler:
        def __init__(self, **kwargs: Any):
            pass

    callbacks_mod = types.ModuleType("langchain_core.callbacks")
    callbacks_mod.BaseCallbackHandler = _BaseCallbackHandler  # type: ignore[attr-defined]

    langchain_core_mod = types.ModuleType("langchain_core")
    langchain_core_mod.callbacks = callbacks_mod  # type: ignore[attr-defined]

    sys.modules["langchain_core"] = langchain_core_mod
    sys.modules["langchain_core.callbacks"] = callbacks_mod


def _install_fake_llamaindex():
    """Inject a minimal llama_index.core mock into sys.modules."""
    if "llama_index" in sys.modules:
        return

    class _CBEventType:
        LLM = "llm"
        EMBEDDING = "embedding"

    class _BaseCallbackHandler:
        def __init__(self, event_starts_to_trace=None, event_ends_to_trace=None, **kw: Any):
            pass

    schema_mod = types.ModuleType("llama_index.core.callbacks.schema")
    schema_mod.CBEventType = _CBEventType  # type: ignore[attr-defined]

    base_handler_mod = types.ModuleType("llama_index.core.callbacks.base_handler")
    base_handler_mod.BaseCallbackHandler = _BaseCallbackHandler  # type: ignore[attr-defined]

    callbacks_mod = types.ModuleType("llama_index.core.callbacks")
    callbacks_mod.base_handler = base_handler_mod  # type: ignore[attr-defined]
    callbacks_mod.schema = schema_mod  # type: ignore[attr-defined]

    core_mod = types.ModuleType("llama_index.core")
    core_mod.callbacks = callbacks_mod  # type: ignore[attr-defined]

    llama_index_mod = types.ModuleType("llama_index")
    llama_index_mod.core = core_mod  # type: ignore[attr-defined]

    sys.modules["llama_index"] = llama_index_mod
    sys.modules["llama_index.core"] = core_mod
    sys.modules["llama_index.core.callbacks"] = callbacks_mod
    sys.modules["llama_index.core.callbacks.base_handler"] = base_handler_mod
    sys.modules["llama_index.core.callbacks.schema"] = schema_mod


# Install fake modules BEFORE any handler imports so the module-level
# _get_base_class() picks up the mocks.
_install_fake_langchain()
_install_fake_llamaindex()


# ---------------------------------------------------------------------------
# LangChain handler tests
# ---------------------------------------------------------------------------


class TestLangChainHandler:
    """Tests for TokenBudgetCallbackHandler (LangChain)."""

    def test_import_error_when_langchain_missing(self):
        """Raise ImportError with install instructions when langchain-core is absent."""
        with patch.dict(sys.modules, {"langchain_core": None}):
            from tokenbudget.integrations.langchain import _check_langchain
            with pytest.raises(ImportError, match="pip install tokenbudget\\[langchain\\]"):
                _check_langchain()

    def test_handler_creation(self):
        """Handler can be instantiated with mocked langchain."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(api_key="tb_ak_test123")
        assert handler._config.api_key == "tb_ak_test123"
        handler.shutdown()

    def test_on_llm_end_captures_usage(self):
        """on_llm_end extracts token counts and sends an event."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(api_key="tb_ak_test123")

        run_id = uuid4()

        # Simulate on_llm_start
        handler.on_llm_start(
            serialized={}, prompts=["Hello"], run_id=run_id,
        )

        # Build a mock LLM response with token usage
        response = MagicMock()
        response.llm_output = {
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "model_name": "gpt-4o",
        }

        # Capture what gets sent to transport
        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_llm_end(response, run_id=run_id)

        assert len(sent_events) == 1
        evt = sent_events[0]
        assert evt.provider == "openai"
        assert evt.model == "gpt-4o"
        assert evt.input_tokens == 10
        assert evt.output_tokens == 20
        assert evt.total_tokens == 30
        assert evt.tags["source"] == "langchain"
        handler.shutdown()

    def test_on_llm_end_detects_anthropic_provider(self):
        """on_llm_end correctly sets provider to anthropic for claude models."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(api_key="tb_ak_test123")

        run_id = uuid4()
        handler.on_llm_start(serialized={}, prompts=["Hi"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {
            "token_usage": {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20},
            "model_name": "claude-sonnet-4-20250514",
        }

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_llm_end(response, run_id=run_id)

        assert sent_events[0].provider == "anthropic"
        assert sent_events[0].model == "claude-sonnet-4-20250514"
        handler.shutdown()

    def test_on_llm_error_cleans_up(self):
        """on_llm_error removes the run from start times."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(api_key="tb_ak_test123")
        run_id = uuid4()
        handler.on_llm_start(serialized={}, prompts=["Hi"], run_id=run_id)
        assert run_id in handler._run_start_times

        handler.on_llm_error(RuntimeError("fail"), run_id=run_id)
        assert run_id not in handler._run_start_times
        handler.shutdown()

    def test_custom_tags_included(self):
        """Custom tags passed at init are included in events."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(
            api_key="tb_ak_test123", tags={"env": "staging"}
        )

        run_id = uuid4()
        handler.on_llm_start(serialized={}, prompts=["Hi"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {
            "token_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "model_name": "gpt-4o",
        }

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)
        handler.on_llm_end(response, run_id=run_id)

        assert sent_events[0].tags["env"] == "staging"
        assert sent_events[0].tags["source"] == "langchain"
        handler.shutdown()

    def test_event_sent_via_transport(self):
        """Events are actually enqueued to the transport queue."""
        from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

        handler = TokenBudgetCallbackHandler(api_key="tb_ak_test123")

        run_id = uuid4()
        handler.on_llm_start(serialized={}, prompts=["Hi"], run_id=run_id)

        response = MagicMock()
        response.llm_output = {
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "model_name": "gpt-4o",
        }

        handler.on_llm_end(response, run_id=run_id)

        # Check event is in the actual transport queue
        assert handler._transport.queue.qsize() == 1
        event = handler._transport.queue.get_nowait()
        assert event.model == "gpt-4o"
        assert event.input_tokens == 10
        handler.shutdown()


# ---------------------------------------------------------------------------
# LlamaIndex handler tests
# ---------------------------------------------------------------------------


class TestLlamaIndexHandler:
    """Tests for TokenBudgetHandler (LlamaIndex)."""

    def test_import_error_when_llamaindex_missing(self):
        """Raise ImportError with install instructions when llama-index-core is absent."""
        with patch.dict(sys.modules, {"llama_index": None, "llama_index.core": None}):
            from tokenbudget.integrations.llamaindex import _check_llamaindex
            with pytest.raises(ImportError, match="pip install tokenbudget\\[llamaindex\\]"):
                _check_llamaindex()

    def test_handler_creation(self):
        """Handler can be instantiated with mocked llama-index."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler

        handler = TokenBudgetHandler(api_key="tb_ak_test123")
        assert handler._config.api_key == "tb_ak_test123"
        handler.shutdown()

    def test_on_event_end_captures_usage(self):
        """on_event_end extracts token counts from LLM events."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler
        from llama_index.core.callbacks.schema import CBEventType

        handler = TokenBudgetHandler(api_key="tb_ak_test123")

        event_id = "evt-123"

        # Start event
        handler.on_event_start(CBEventType.LLM, payload={}, event_id=event_id)

        # Build payload with token usage
        payload = {
            "prompt_tokens": 15,
            "completion_tokens": 25,
        }

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_event_end(CBEventType.LLM, payload=payload, event_id=event_id)

        assert len(sent_events) == 1
        evt = sent_events[0]
        assert evt.input_tokens == 15
        assert evt.output_tokens == 25
        assert evt.total_tokens == 40
        assert evt.tags["source"] == "llamaindex"
        handler.shutdown()

    def test_non_llm_events_ignored(self):
        """Non-LLM events are ignored."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler
        from llama_index.core.callbacks.schema import CBEventType

        handler = TokenBudgetHandler(api_key="tb_ak_test123")

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_event_end(CBEventType.EMBEDDING, payload={}, event_id="evt-456")

        assert len(sent_events) == 0
        handler.shutdown()

    def test_on_event_end_with_raw_response(self):
        """on_event_end extracts usage from raw dict response."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler
        from llama_index.core.callbacks.schema import CBEventType

        handler = TokenBudgetHandler(api_key="tb_ak_test123")

        event_id = "evt-789"
        handler.on_event_start(CBEventType.LLM, payload={}, event_id=event_id)

        # Simulate a response with raw dict containing usage
        mock_response = MagicMock()
        mock_response.raw = {
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
            "model": "gpt-4o",
        }
        payload = {"response": mock_response}

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_event_end(CBEventType.LLM, payload=payload, event_id=event_id)

        assert len(sent_events) == 1
        evt = sent_events[0]
        assert evt.input_tokens == 50
        assert evt.output_tokens == 100
        assert evt.model == "gpt-4o"
        assert evt.provider == "openai"
        handler.shutdown()

    def test_custom_tags_included(self):
        """Custom tags are included in events."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler
        from llama_index.core.callbacks.schema import CBEventType

        handler = TokenBudgetHandler(
            api_key="tb_ak_test123", tags={"team": "ml"}
        )

        event_id = "evt-tags"
        handler.on_event_start(CBEventType.LLM, payload={}, event_id=event_id)

        sent_events: list = []
        handler._transport.send = lambda evt: sent_events.append(evt)

        handler.on_event_end(
            CBEventType.LLM,
            payload={"prompt_tokens": 1, "completion_tokens": 1},
            event_id=event_id,
        )

        assert sent_events[0].tags["team"] == "ml"
        assert sent_events[0].tags["source"] == "llamaindex"
        handler.shutdown()

    def test_event_sent_via_transport(self):
        """Events are actually enqueued to the transport queue."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler
        from llama_index.core.callbacks.schema import CBEventType

        handler = TokenBudgetHandler(api_key="tb_ak_test123")

        event_id = "evt-transport"
        handler.on_event_start(CBEventType.LLM, payload={}, event_id=event_id)
        handler.on_event_end(
            CBEventType.LLM,
            payload={"prompt_tokens": 5, "completion_tokens": 10},
            event_id=event_id,
        )

        assert handler._transport.queue.qsize() == 1
        event = handler._transport.queue.get_nowait()
        assert event.input_tokens == 5
        assert event.output_tokens == 10
        handler.shutdown()

    def test_start_trace_and_end_trace_are_noops(self):
        """start_trace and end_trace don't raise."""
        from tokenbudget.integrations.llamaindex import TokenBudgetHandler

        handler = TokenBudgetHandler(api_key="tb_ak_test123")
        handler.start_trace("trace-1")
        handler.end_trace("trace-1", trace_map={})
        handler.shutdown()
