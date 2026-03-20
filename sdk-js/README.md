# @tokenbudget/sdk

Know exactly what your AI agents cost. Zero-dependency TypeScript SDK for tracking OpenAI and Anthropic token usage.

## Installation

```bash
npm install @tokenbudget/sdk
```

## Quick Start

### OpenAI

```typescript
import { wrapOpenAI } from '@tokenbudget/sdk'
import OpenAI from 'openai'

const client = wrapOpenAI(new OpenAI(), { apiKey: 'tb_ak_...' })

const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello!' }],
})
// Automatically tracked — cost, tokens, latency
```

### Anthropic

```typescript
import { wrapAnthropic } from '@tokenbudget/sdk'
import Anthropic from '@anthropic-ai/sdk'

const client = wrapAnthropic(new Anthropic(), { apiKey: 'tb_ak_...' })

const response = await client.messages.create({
  model: 'claude-sonnet-4-20250514',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello!' }],
})
// Automatically tracked
```

### Tags for Attribution

```typescript
import { wrapOpenAI, tags } from '@tokenbudget/sdk'
import OpenAI from 'openai'

const client = wrapOpenAI(new OpenAI(), { apiKey: 'tb_ak_...' })

// Tag requests with feature/user context
const response = await tags({ feature: 'chat', userId: 'u_123' }, async () => {
  return client.chat.completions.create({
    model: 'gpt-4o',
    messages: [{ role: 'user', content: 'Hello!' }],
  })
})
```

### Manual Tracking

```typescript
import { configure, track, shutdown } from '@tokenbudget/sdk'

configure({ apiKey: 'tb_ak_...' })

track({
  provider: 'openai',
  model: 'gpt-4o',
  input_tokens: 100,
  output_tokens: 50,
  total_tokens: 150,
  cost_usd: 0.00075,
  latency_ms: 320,
})

// On app shutdown
await shutdown()
```

## Configuration

| Option           | Default                        | Description                              |
| ---------------- | ------------------------------ | ---------------------------------------- |
| `apiKey`         | `TOKENBUDGET_API_KEY` env var  | TokenBudget API key                      |
| `endpoint`       | `https://api.tokenbudget.com`  | API endpoint                             |
| `enabled`        | `true`                         | Enable/disable tracking                  |
| `flushIntervalMs`| `1000`                         | Flush interval in milliseconds           |
| `batchSize`      | `10`                           | Max events per batch before auto-flush   |
| `maxQueueSize`   | `1000`                         | Max queue size before dropping events    |

## Requirements

- Node.js 18+ (uses built-in `fetch`)
- Zero external dependencies

## License

Apache-2.0
