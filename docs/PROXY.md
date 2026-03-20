# TokenBudget Transparent Proxy

TokenBudget's proxy mode lets you track AI usage **without changing any application code**.
Just point your OpenAI or Anthropic client at TokenBudget and we forward every request
transparently while silently recording token usage and cost.

---

## Security Guarantees

| Guarantee | How |
|-----------|-----|
| Your upstream API key is **never stored** | We read it from the request header, forward it, then discard it immediately — it never touches a database or log line. |
| Your upstream API key is **never logged** | The `Authorization` / `x-api-key` header values are explicitly excluded from all logging. |
| Requests are **forwarded unchanged** | The full request body, model name, temperature, tools, etc. are passed through byte-for-byte. |
| Responses are **forwarded unchanged** | Status code, body, and content-type are mirrored exactly. |
| Recording **never blocks** your response | Events are written via a FastAPI `BackgroundTask` after the response is returned to the caller. |

---

## Proxy Endpoints

| Method | Path | Upstream |
|--------|------|----------|
| POST | `/proxy/openai/v1/chat/completions` | `https://api.openai.com/v1/chat/completions` |
| POST | `/proxy/openai/v1/completions` | `https://api.openai.com/v1/completions` |
| POST | `/proxy/openai/v1/embeddings` | `https://api.openai.com/v1/embeddings` |
| POST | `/proxy/anthropic/v1/messages` | `https://api.anthropic.com/v1/messages` |

---

## Required Headers

| Header | Description |
|--------|-------------|
| `X-TokenBudget-Key` | Your TokenBudget API key (starts with `tb_ak_`). Optional — if missing or invalid, the request is still proxied but usage is not recorded. |
| `Authorization` | Your **real** OpenAI API key (`Bearer sk-...`). Required for OpenAI endpoints. |
| `x-api-key` | Your **real** Anthropic API key. Required for Anthropic endpoints. |

---

## Optional Metadata Headers

These headers are recorded as tags on the event but are **never forwarded** to upstream:

| Header | Example | Description |
|--------|---------|-------------|
| `X-TB-Feature` | `"chat"` | Tag by product feature |
| `X-TB-User` | `"user_123"` | Associate with an end-user |
| `X-TB-Project` | `"my-app"` | Override project |
| `X-TB-Tags` | `{"env":"prod"}` | JSON object of arbitrary tags |

---

## Quick Start — OpenAI Python

```python
import openai

client = openai.OpenAI(
    api_key="YOUR_OPENAI_API_KEY",
    base_url="https://your-tokenbudget-instance.com/proxy/openai/v1",
    default_headers={"X-TokenBudget-Key": "tb_ak_your_key"},
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

## Quick Start — Anthropic Python

```python
import anthropic

client = anthropic.Anthropic(
    api_key="YOUR_ANTHROPIC_API_KEY",
    base_url="https://your-tokenbudget-instance.com/proxy/anthropic",
    default_headers={"X-TokenBudget-Key": "tb_ak_your_key"},
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}],
)
```

## Quick Start — Node.js

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_OPENAI_API_KEY",
  baseURL: "https://your-tokenbudget-instance.com/proxy/openai/v1",
  defaultHeaders: { "X-TokenBudget-Key": "tb_ak_your_key" },
});

const completion = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});
```

---

## Streaming

Streaming (`"stream": true`) is fully supported.
Chunks are forwarded as they arrive.  Usage data is parsed from the final SSE chunk and
recorded after the stream completes.

---

## Error Handling

Upstream errors (4xx / 5xx) are forwarded **unchanged** to the caller.
If a TokenBudget key is present, the error is recorded with `error: true` in the event
metadata so you can monitor failure rates in Analytics.

---

## Response Header

Every proxied response includes:

```
X-Proxied-By: TokenBudget/1.0
```

---

## Built-in Pricing

Costs are calculated automatically using the built-in pricing table (`api/app/lib/pricing.py`).
Model names are matched using longest-prefix fuzzy matching, so versioned variants like
`gpt-4o-2024-11-20` resolve correctly to `gpt-4o` pricing.  Unknown models record
`cost_usd = 0.0` but tokens are still tracked.

| Model | Input / 1K tokens | Output / 1K tokens |
|-------|------------------|--------------------|
| gpt-4o | $0.0025 | $0.0100 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-4-turbo | $0.0100 | $0.0300 |
| gpt-4 | $0.0300 | $0.0600 |
| gpt-3.5-turbo | $0.0005 | $0.0015 |
| text-embedding-3-small | $0.00002 | — |
| text-embedding-3-large | $0.00013 | — |
| claude-opus-4 | $0.0150 | $0.0750 |
| claude-sonnet-4 | $0.0030 | $0.0150 |
| claude-haiku-4 | $0.00025 | $0.00125 |
| claude-3-5-sonnet | $0.0030 | $0.0150 |
| claude-3-5-haiku | $0.0008 | $0.0040 |
