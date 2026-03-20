# TokenBudget SDK — Developer Documentation

## Overview

The TokenBudget Python SDK wraps existing OpenAI and Anthropic clients to automatically track token usage, cost, and latency. It operates entirely in the background — zero latency impact on your API calls.

## Installation

```bash
pip install tokenbudget

# With provider extras (optional, for type hints)
pip install tokenbudget[openai]
pip install tokenbudget[anthropic]
```

## Quick Start

```python
import openai
import tokenbudget

client = tokenbudget.wrap(
    openai.Client(),
    api_key="tb_ak_your_key_here",
    endpoint="http://localhost:2727"  # or https://api.tokenbudget.com
)

# Use exactly as before — everything is tracked automatically
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Module Reference

### `tokenbudget/__init__.py`
Public API exports:
- `wrap(client, api_key, endpoint, **kwargs)` → patched client
- `shutdown()` → flush remaining events and close
- `tags(**kwargs)` → context manager for event tagging
- `tagged(**kwargs)` → decorator for event tagging
- `TokenBudgetConfig` → configuration dataclass

---

### `tokenbudget/client.py`

#### `wrap(client, api_key="", endpoint="", **kwargs)`
Patches an OpenAI or Anthropic client to track usage events.

- **client**: An `openai.Client()` or `anthropic.Anthropic()` instance
- **api_key**: TokenBudget API key (or set `TOKENBUDGET_API_KEY` env var)
- **endpoint**: API endpoint (default: `https://api.tokenbudget.com`)
- **Returns**: The same client object, patched in-place
- **Thread-safe**: Yes — uses a singleton transport with thread-safe queue

```python
# The client is mutated in place — both references work
client = openai.Client()
wrapped = tokenbudget.wrap(client, api_key="tb_ak_...")
assert client is wrapped  # True — same object
```

#### `shutdown()`
Flushes any remaining queued events and closes the HTTP transport. Call this before your process exits for clean shutdown.

```python
import atexit
atexit.register(tokenbudget.shutdown)
```

---

### `tokenbudget/config.py`

#### `TokenBudgetConfig`
Dataclass holding SDK configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | str | `""` | API key (falls back to `TOKENBUDGET_API_KEY` env) |
| `endpoint` | str | `"https://api.tokenbudget.com"` | API endpoint URL |
| `enabled` | bool | `True` | Master switch to disable tracking |
| `flush_interval` | float | `1.0` | Seconds between background flushes |
| `max_queue_size` | int | `1000` | Max events in queue before dropping |

Raises `ValueError` if no API key is provided (inline or env var).

---

### `tokenbudget/types.py`

#### `UsageEvent`
Dataclass representing a single tracked API call.

| Field | Type | Description |
|-------|------|-------------|
| `provider` | str | `"openai"` or `"anthropic"` |
| `model` | str | Model name (e.g., `"gpt-4o"`) |
| `input_tokens` | int | Input/prompt token count |
| `output_tokens` | int | Output/completion token count |
| `total_tokens` | int | Sum of input + output |
| `cost_usd` | float | Calculated cost in USD |
| `latency_ms` | int | Wall-clock latency of the API call |
| `tags` | dict | User-defined tags from `tags()` context |
| `metadata` | dict | Additional metadata |
| `timestamp` | float | Unix timestamp (auto-set) |

---

### `tokenbudget/pricing.py`

#### `PRICING: dict[str, dict[str, float]]`
Lookup table mapping model names to per-token costs.

Currently supported models:
| Model | Input (per token) | Output (per token) |
|-------|-------------------|-------------------|
| gpt-4 | $0.00003 | $0.00006 |
| gpt-4-turbo | $0.00001 | $0.00003 |
| gpt-4o | $0.0000025 | $0.00001 |
| gpt-4o-mini | $0.00000015 | $0.0000006 |
| gpt-3.5-turbo | $0.0000005 | $0.0000015 |
| claude-sonnet-4-20250514 | $0.000003 | $0.000015 |
| claude-opus-4-20250514 | $0.000015 | $0.000075 |
| claude-haiku-4-5-20251001 | $0.0000008 | $0.000004 |

#### `calculate_cost(model, input_tokens, output_tokens) -> float`
Returns the estimated cost in USD. Returns `0.0` for unknown models.

---

### `tokenbudget/transport.py`

#### `EventTransport`
Background event sender using a thread-safe queue and daemon flush thread.

**Key behaviors:**
- Events are queued via `send(event)` — never blocks the caller
- A daemon thread calls `flush_sync()` every `flush_interval` seconds
- Flush sends a batch POST to `/v1/events/batch`
- On HTTP error or network failure: events are re-queued for retry
- Queue overflow: events are silently dropped (fire-and-forget)
- `shutdown()`: flushes remaining events and closes the httpx client

---

### `tokenbudget/context.py`

#### `tags(**kwargs)` — Context Manager
Sets tags for all events created within the block. Tags are inherited and merged in nested contexts.

```python
with tokenbudget.tags(feature="chatbot", env="production"):
    # All API calls here are tagged with feature=chatbot, env=production
    response = client.chat.completions.create(...)

    with tokenbudget.tags(user_id="u_123"):
        # Tags: feature=chatbot, env=production, user_id=u_123
        response2 = client.chat.completions.create(...)
```

#### `tagged(**kwargs)` — Decorator
Function decorator that wraps the body in a `tags()` context.

```python
@tokenbudget.tagged(feature="code-review")
def review_code(code: str):
    return client.chat.completions.create(...)
```

#### `get_current_tags() -> dict`
Returns a copy of the current tag context. Empty dict if no tags are active.

**Implementation**: Uses `contextvars.ContextVar` — fully async-safe and thread-safe.

---

### `tokenbudget/providers/`

#### `base.py` — `BaseProvider` (Abstract)
| Method | Description |
|--------|-------------|
| `detect(client) -> bool` | Returns True if this provider handles the client type |
| `extract_event(response, latency_ms) -> UsageEvent` | Extracts usage data from API response |
| `patch(client, transport) -> None` | Monkey-patches the client's create method |

#### `openai.py` — `OpenAIProvider`
- **Detects**: Clients where `type(client).__module__` starts with `"openai"`
- **Patches**: `client.chat.completions.create`
- **Extracts**: `response.usage.prompt_tokens`, `response.usage.completion_tokens`, `response.model`
- **Error handling**: All extraction/sending wrapped in try/except — never breaks user code

#### `anthropic.py` — `AnthropicProvider`
- **Detects**: Clients where `type(client).__module__` starts with `"anthropic"`
- **Patches**: `client.messages.create`
- **Extracts**: `response.usage.input_tokens`, `response.usage.output_tokens`, `response.model`

#### `__init__.py` — Provider Registry
- `PROVIDERS`: List of all provider instances `[OpenAIProvider(), AnthropicProvider()]`
- `detect_provider(client)`: Iterates providers, returns first match or raises `ValueError`

---

## Test Coverage

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_config.py` | 8 | Config loading, env vars, defaults, validation |
| `test_pricing.py` | 8 | Cost calculation, all models, unknown model handling |
| `test_transport.py` | 9 | Queue, flush, retry, error handling |
| `test_context.py` | 13 | Tags, nesting, decorator, clearing |
| `test_openai_provider.py` | 9 | Detection, extraction, patching, error safety |
| `test_anthropic_provider.py` | 9 | Detection, extraction, patching, tagging |
| `test_client.py` | 7 | wrap(), shutdown(), provider detection |
| **Total** | **65** | |

Run tests: `cd sdk && pip install -e ".[dev]" && pytest -v`

---

## AWS Bedrock Support

Track token usage for AWS Bedrock models (Anthropic Claude, Amazon Titan, Meta Llama, etc.).

### Installation

```bash
pip install tokenbudget[bedrock]
```

This installs the `boto3` dependency required for Bedrock integration.

### Usage

```python
import boto3
import tokenbudget

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

# Wrap the Bedrock client — all invoke_model calls are now tracked
wrapped = tokenbudget.wrap_bedrock(
    bedrock,
    api_key="tb_ak_your_key_here",
    endpoint="https://api.tokenbudget.com"
)

# Use exactly as before
response = wrapped.invoke_model(
    modelId="anthropic.claude-sonnet-4-20250514-v1:0",
    body='{"prompt": "Hello!", "max_tokens": 100}'
)
```

`wrap_bedrock()` intercepts `invoke_model` and `invoke_model_with_response_stream` calls, extracting token counts from the Bedrock response metadata. Reasoning tokens are tracked automatically for supported models (Claude o-series equivalents).

---

## LangChain Callback Handler

Automatically track all LLM calls made through LangChain.

### Installation

```bash
pip install tokenbudget[langchain]
```

### Usage

```python
from langchain_openai import ChatOpenAI
from tokenbudget.integrations.langchain import TokenBudgetCallbackHandler

handler = TokenBudgetCallbackHandler(
    api_key="tb_ak_your_key_here",
    endpoint="https://api.tokenbudget.com"
)

llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])

# All calls through this LLM are tracked automatically
response = llm.invoke("Explain quantum computing in one sentence.")
```

The callback handler hooks into `on_llm_end` to extract token usage from the LangChain `LLMResult` object. Tags can be passed via the handler constructor:

```python
handler = TokenBudgetCallbackHandler(
    api_key="tb_ak_...",
    tags={"feature": "qa-chain", "env": "production"}
)
```

---

## LlamaIndex Callback Handler

Automatically track all LLM calls made through LlamaIndex.

### Installation

```bash
pip install tokenbudget[llamaindex]
```

### Usage

```python
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager
from tokenbudget.integrations.llamaindex import TokenBudgetLlamaIndexHandler

handler = TokenBudgetLlamaIndexHandler(
    api_key="tb_ak_your_key_here",
    endpoint="https://api.tokenbudget.com"
)

Settings.callback_manager = CallbackManager([handler])
llm = OpenAI(model="gpt-4o")

# All LLM calls are tracked
response = llm.complete("What is the meaning of life?")
```

The handler listens to `CBEventType.LLM` events and extracts token usage from the event payload. Tags are supported the same way as the LangChain handler:

```python
handler = TokenBudgetLlamaIndexHandler(
    api_key="tb_ak_...",
    tags={"feature": "rag-pipeline"}
)
```
