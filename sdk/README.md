# TokenBudget

> Open source AI cost tracking. One line to start tracking.

## Install

```bash
pip install tokenbudget
```

## Quick Start

```python
import openai, tokenbudget

client = tokenbudget.wrap(
    openai.Client(),
    api_key="tb_ak_..."  # free at tokenbudget.com
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# Everything tracked automatically in your dashboard
```

## Anthropic Support

```python
import anthropic, tokenbudget

client = tokenbudget.wrap(
    anthropic.Anthropic(),
    api_key="tb_ak_..."
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Features

- **One line integration** — wrap your existing client, done
- **Zero latency impact** — tracking runs in background
- **Feature tagging** — know cost per feature, user, project
- **Multi-provider** — OpenAI + Anthropic (Gemini coming soon)
- **Privacy first** — we never store prompts, responses, or API keys

## Tagging

```python
with tokenbudget.tags(feature="chatbot", user_id="user-123"):
    response = client.chat.completions.create(...)
```

## Dashboard

See your costs at [tokenbudget.com](https://tokenbudget.com) — broken down by
feature, user, model, and project.

## Self-Hosting

```bash
git clone https://github.com/AIMasterLabs/tokenbudget
cd tokenbudget
docker compose up -d
```

## License

Apache 2.0 — Free for personal and open source use.
Commercial use requires license. See [LICENSE](../LICENSE).
