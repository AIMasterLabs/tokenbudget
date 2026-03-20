# TokenBudget

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI version](https://badge.fury.io/py/tokenbudget.svg)](https://badge.fury.io/py/tokenbudget)

Open source AI cost tracking. Know exactly what your AI costs — per feature, per user, per project.

**You keep your own API keys.** TokenBudget never stores them. It sits between your app and OpenAI/Anthropic, recording only token counts and costs. You get a real-time dashboard showing where every dollar goes.

## Who Is This For

- **Startups using AI APIs** — track costs before they surprise you
- **Teams with multiple AI features** — see which feature costs the most
- **Companies with per-customer AI usage** — know your cost per user
- **Anyone who got a shocking AI bill** — never again

## How It Works

```
Your App  →  TokenBudget (proxy or SDK)  →  OpenAI / Anthropic
                    ↓
              Records: tokens, cost, model, latency
              Never records: prompts, responses, API keys
                    ↓
              Dashboard: costs by feature, user, project
```

## Deploy With Docker (5 minutes)

### Step 1: Clone and start

```bash
git clone https://github.com/AIMasterLabs/tokenbudget
cd tokenbudget
docker compose up -d
```

This starts 4 containers:
- **PostgreSQL** (port 5432) — stores events and config
- **Redis** (port 6379) — caching and rate limiting
- **API** (port 2727) — FastAPI backend
- **Dashboard** (port 3000) — React frontend

### Step 2: Verify

```bash
# Linux/Mac
curl http://localhost:2727/health

# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:2727/health"
```

You should see: `{"status":"ok","version":"0.2.0","db":"connected","redis":"connected"}`

### Step 3: Create your first API key

```bash
# Linux/Mac
curl -X POST http://localhost:2727/api/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app"}'

# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:2727/api/keys" `
  -Method POST -ContentType "application/json" `
  -Body '{"name":"my-app"}'
```

Save the `raw_key` from the response — it starts with `tb_ak_` and is shown only once.

### Step 4: Start tracking

Pick one of three integration methods below.

## Integration Methods

### Method 1: Python SDK (one line change)

```bash
pip install tokenbudget
```

```python
import openai
import tokenbudget

# Wrap your existing client — everything else stays the same
client = tokenbudget.wrap(
    openai.Client(),
    api_key="tb_ak_YOUR_KEY",
    endpoint="http://localhost:2727"  # your TokenBudget server
)

# Use as normal — costs tracked automatically in background
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
```

Works with Anthropic too:
```python
import anthropic
import tokenbudget

client = tokenbudget.wrap(
    anthropic.Anthropic(),
    api_key="tb_ak_YOUR_KEY",
    endpoint="http://localhost:2727"
)
```

Tag by feature and user to see cost breakdowns:
```python
with tokenbudget.tags(feature="chatbot", user_id="user-123"):
    response = client.chat.completions.create(...)
```

### Method 2: Proxy (zero code change)

Point your OpenAI client to TokenBudget instead. Your API key passes through — we never store it.

```python
import openai

client = openai.OpenAI(
    api_key="sk-your-openai-key",           # your real OpenAI key
    base_url="http://localhost:2727/proxy/openai/v1",  # your TokenBudget server
    default_headers={
        "X-TokenBudget-Key": "tb_ak_YOUR_KEY",
        "X-TB-Feature": "chatbot",           # optional: tag by feature
        "X-TB-User": "user-123",             # optional: tag by user
    }
)

# Use exactly as before — works with streaming too
response = client.chat.completions.create(model="gpt-4o", messages=[...])
```

Works with any language — just change the base URL:
```javascript
// Node.js
const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: "http://localhost:2727/proxy/openai/v1",
    defaultHeaders: { "X-TokenBudget-Key": "tb_ak_YOUR_KEY" }
});
```

### Method 3: Direct API (any language)

Send events directly after your AI calls. Works from any language.

```bash
curl -X POST http://localhost:2727/v1/events \
  -H "Authorization: Bearer tb_ak_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4o",
    "input_tokens": 1500,
    "output_tokens": 300,
    "total_tokens": 1800,
    "cost_usd": 0.027,
    "latency_ms": 850,
    "feature": "chatbot",
    "user_id": "user-123"
  }'
```

### Step 5: Set up authentication

TokenBudget supports 3 auth modes. Set `AUTH_MODE` in your `.env` file:

| Mode | What It Does | Best For |
|------|-------------|----------|
| `local` | Email + password login with JWT tokens (default) | Teams, self-hosted |
| `clerk` | Google OAuth + magic link via Clerk | SaaS deployment |
| `none` | No login, auto-provisions API key on first visit | Single user, personal |

**For `local` mode (default):**

1. Open http://localhost:3000 (Docker) or http://localhost:5173 (dev mode)
2. Click "Create Account" to register
3. First user registered automatically becomes **admin**
4. Admin can add more users at Dashboard > Users

**User roles:**

| Role | Can Do |
|------|--------|
| Admin | See all projects, manage users, full access |
| Member | See assigned projects only, create events |
| Viewer | Read-only access to assigned projects |

Admins assign users to specific projects — members only see projects they belong to. This keeps department costs private (e.g., a marketing team can't see R&D's AI spend on a secret project).

**For `clerk` mode:** Set `CLERK_SECRET_KEY` and `CLERK_PUBLISHABLE_KEY` in `.env`. Users log in with Google or magic link.

**For `none` mode:** Dashboard opens immediately with no login. Good for personal use or development.

## Deploy Without Docker

For development or if you prefer running services directly.

**Prerequisites:** Python 3.11+, Node 18+, PostgreSQL, Redis

**1. Database and cache:**
Start PostgreSQL and Redis however you prefer (local install, Docker, cloud).

**2. API server:**
```bash
cd api
cp .env.example .env
# Edit .env — set DATABASE_URL and REDIS_URL to your instances
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 2727
```

**3. Dashboard:**
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local — set VITE_API_URL to your API (e.g. http://localhost:2727)
npm install
npm run dev
```

**4. Verify:**
```bash
curl http://localhost:2727/health
```

## What Gets Stored

Each API call creates one event (~300 bytes):

| Field | Example | Purpose |
|-------|---------|---------|
| provider | openai | Which AI provider |
| model | gpt-4o | Which model |
| input_tokens | 1,500 | Tokens sent |
| output_tokens | 300 | Tokens received |
| cost_usd | $0.027 | Calculated cost |
| latency_ms | 850 | Response time |
| feature | chatbot | Your tag (optional) |
| user_id | user-123 | Your tag (optional) |

**Never stored:** prompts, responses, your AI API keys, IP addresses, PII.

## Security

- Your OpenAI/Anthropic API keys **pass through the proxy and are never logged or stored**
- All API key hashes use SHA-256 with Redis caching
- Rate limiting on all endpoints
- Input validation on all fields
- CORS configurable per environment

## Architecture

```
                    ┌─────────────────────┐
  Your App ────────>│   TokenBudget API   │────────> OpenAI / Anthropic
  (SDK or Proxy)    │   (FastAPI)         │          (your key passes through)
                    └────────┬────────────┘
                             │ records event
                    ┌────────v────────────┐
                    │   PostgreSQL        │
                    │   (events, config)  │
                    └─────────────────────┘
                    ┌─────────────────────┐
                    │   Redis             │
                    │   (cache, rate limit)│
                    └─────────────────────┘
                    ┌─────────────────────┐
  You ─────────────>│   React Dashboard   │
                    │   (costs, budgets)  │
                    └─────────────────────┘
```

## Configuration

All settings are via environment variables. See `.env.example` for the full list.

Key settings:
| Variable | Default | Purpose |
|----------|---------|---------|
| DATABASE_URL | postgresql+asyncpg://... | PostgreSQL connection |
| REDIS_URL | redis://localhost:6379 | Redis connection |
| SECRET_KEY | change-me-in-production | Session security |
| CORS_ORIGINS | http://localhost:5173 | Allowed frontend origins |
| SIGNUPS_ENABLED | true | Kill switch for new signups |

## Completely Free & Open Source

TokenBudget is completely free. There are no paid tiers, no Pro plans, no Enterprise upsells. Every feature is available to everyone. Self-host it, modify it, use it in production -- it is yours.

We believe cost tracking for AI should be accessible to every developer and every team, regardless of budget.

## Development

**Run the full stack locally:**

```bash
# Start infrastructure (Postgres + Redis)
docker compose up -d db redis

# API server
cd api
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 2727

# Frontend
cd frontend
npm install
npm run dev
```

**Run tests:**

```bash
# API tests
cd api && python -m pytest tests/ -q

# SDK tests
cd sdk && python -m pytest tests/ -q

# Frontend type-check
cd frontend && npx tsc --noEmit
```

**Lint:**

```bash
# Python
cd api && ruff check . && ruff format --check .

# Frontend
cd frontend && npx eslint src/
```

## Contributing

We welcome contributions of all kinds -- bug fixes, new features, documentation improvements, and more.

1. Fork the repo and create a feature branch
2. Make your changes following the existing code style (see `CLAUDE.md` for conventions)
3. Add tests for new functionality
4. Run the test suite to make sure everything passes
5. Open a pull request with a clear description of the change

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Documentation

| Doc | What It Covers |
|-----|---------------|
| [docs/API.md](docs/API.md) | All API endpoints and examples |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [docs/AUTH.md](docs/AUTH.md) | Authentication system (API keys + Clerk) |
| [docs/SDK.md](docs/SDK.md) | Python SDK reference |
| [docs/PROXY.md](docs/PROXY.md) | Proxy setup for OpenAI and Anthropic |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Scaling and optimization |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Dashboard components and pages |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API | Python, FastAPI, SQLAlchemy 2.0, asyncpg |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Dashboard | React 18, TypeScript, Vite, Tailwind, Recharts |
| SDK | Python 3.9+ (pip install tokenbudget) |
| Auth | Clerk (optional) + API key (always) |
| Deploy | Docker Compose, Railway, Vercel |

## License

Apache 2.0 -- free for everyone. See [LICENSE](LICENSE).
