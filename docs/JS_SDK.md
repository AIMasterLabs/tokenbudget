# TokenBudget JavaScript/TypeScript SDK — Developer Documentation

## Overview

The TokenBudget JS/TS SDK wraps existing OpenAI and Anthropic clients to automatically track token usage, cost, and latency. It operates entirely in the background with zero latency impact on your API calls.

## Installation

```bash
npm install @tokenbudget/sdk
# or
yarn add @tokenbudget/sdk
# or
pnpm add @tokenbudget/sdk
```

## Quick Start

```typescript
import OpenAI from "openai";
import { wrapOpenAI } from "@tokenbudget/sdk";

const client = wrapOpenAI(new OpenAI(), {
  apiKey: "tb_ak_your_key_here",
  endpoint: "https://api.tokenbudget.com",
});

// Use exactly as before — everything is tracked automatically
const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});
```

---

## API Reference

### `wrapOpenAI(client, config)`

Wraps an OpenAI client instance to track all `chat.completions.create` calls.

```typescript
import OpenAI from "openai";
import { wrapOpenAI } from "@tokenbudget/sdk";

const openai = new OpenAI();
const tracked = wrapOpenAI(openai, {
  apiKey: "tb_ak_...",
  endpoint: "https://api.tokenbudget.com",
});

// Both streaming and non-streaming are tracked
const response = await tracked.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});
```

**Parameters:**
- `client` — An `OpenAI` instance
- `config` — Configuration object (see [Configuration](#configuration))

**Returns:** The same client, patched in-place (the reference is identical).

---

### `wrapAnthropic(client, config)`

Wraps an Anthropic client instance to track all `messages.create` calls.

```typescript
import Anthropic from "@anthropic-ai/sdk";
import { wrapAnthropic } from "@tokenbudget/sdk";

const anthropic = new Anthropic();
const tracked = wrapAnthropic(anthropic, {
  apiKey: "tb_ak_...",
  endpoint: "https://api.tokenbudget.com",
});

const response = await tracked.messages.create({
  model: "claude-sonnet-4-20250514",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello!" }],
});
```

**Parameters:**
- `client` — An `Anthropic` instance
- `config` — Configuration object (see [Configuration](#configuration))

**Returns:** The same client, patched in-place.

---

### `tags(tagMap)`

Returns a context object for tagging events. Tags are attached to all tracked API calls made within the context.

```typescript
import { tags } from "@tokenbudget/sdk";

// Using async context
const ctx = tags({ feature: "chatbot", env: "production" });
await ctx.run(async () => {
  // All API calls here get tagged with feature=chatbot, env=production
  const response = await client.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "Hello!" }],
  });
});
```

Tags can be nested and are merged (inner tags override outer tags with the same key):

```typescript
const outer = tags({ feature: "chatbot", env: "production" });
await outer.run(async () => {
  const inner = tags({ user_id: "u_123" });
  await inner.run(async () => {
    // Tags: { feature: "chatbot", env: "production", user_id: "u_123" }
    await client.chat.completions.create({ ... });
  });
});
```

---

### `shutdown()`

Flushes any remaining queued events and closes the transport. Call before your process exits.

```typescript
import { shutdown } from "@tokenbudget/sdk";

process.on("beforeExit", async () => {
  await shutdown();
});
```

---

## Configuration

The config object passed to `wrapOpenAI` / `wrapAnthropic`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `apiKey` | string | `process.env.TOKENBUDGET_API_KEY` | TokenBudget API key |
| `endpoint` | string | `"https://api.tokenbudget.com"` | API endpoint URL |
| `enabled` | boolean | `true` | Master switch to disable tracking |
| `flushIntervalMs` | number | `1000` | Milliseconds between background flushes |
| `maxQueueSize` | number | `1000` | Max events in queue before dropping |

If no `apiKey` is provided inline, the SDK reads from the `TOKENBUDGET_API_KEY` environment variable. An error is thrown if neither is set.

---

## Reasoning Token Tracking

The SDK automatically tracks reasoning tokens for models that support them (OpenAI o1, o3, o4-mini; Anthropic Claude with extended thinking). The `reasoning_tokens` field is extracted from the API response and included in the usage event.

```typescript
const response = await client.chat.completions.create({
  model: "o4-mini",
  messages: [{ role: "user", content: "Solve this math problem..." }],
});
// Event automatically includes reasoning_tokens from response.usage.completion_tokens_details.reasoning_tokens
```

---

## Usage Event Schema

Each tracked API call produces an event with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `provider` | string | `"openai"` or `"anthropic"` |
| `model` | string | Model name (e.g., `"gpt-4o"`) |
| `input_tokens` | number | Input/prompt token count |
| `output_tokens` | number | Output/completion token count |
| `reasoning_tokens` | number | Reasoning/thinking tokens (0 if not applicable) |
| `total_tokens` | number | Sum of input + output |
| `cost_usd` | number | Calculated cost in USD |
| `latency_ms` | number | Wall-clock latency of the API call |
| `tags` | object | User-defined tags from `tags()` context |
| `metadata` | object | Additional metadata |

---

## Transport

Events are sent in the background using `fetch`. The transport:

- Queues events via an internal array (never blocks the caller)
- Flushes every `flushIntervalMs` milliseconds
- Sends a batch POST to `/v1/events/batch` with Bearer API key auth
- On HTTP error or network failure: events are re-queued for retry
- Queue overflow: events are silently dropped (fire-and-forget)

---

## Examples

### Next.js API Route

```typescript
import OpenAI from "openai";
import { wrapOpenAI, tags } from "@tokenbudget/sdk";

const client = wrapOpenAI(new OpenAI(), {
  apiKey: process.env.TOKENBUDGET_API_KEY,
});

export async function POST(request: Request) {
  const { message, userId } = await request.json();

  const ctx = tags({ feature: "chat-api", user_id: userId });
  return ctx.run(async () => {
    const response = await client.chat.completions.create({
      model: "gpt-4o",
      messages: [{ role: "user", content: message }],
    });
    return Response.json({ reply: response.choices[0].message.content });
  });
}
```

### Express.js Middleware

```typescript
import { tags } from "@tokenbudget/sdk";

function trackingMiddleware(req, res, next) {
  const ctx = tags({
    feature: req.path,
    user_id: req.user?.id,
    env: process.env.NODE_ENV,
  });
  ctx.run(() => next());
}
```
