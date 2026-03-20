# TokenBudget — Architecture Documentation

## System Overview

```
┌─────────────────┐     async POST      ┌──────────────────┐     SQL      ┌────────────┐
│  Your Python App │ ──────────────────→ │  FastAPI Backend  │ ──────────→ │ PostgreSQL │
│                  │                     │  (port 8000)      │             │  (port 5432)│
│  tokenbudget.wrap│  background thread  │                   │             └────────────┘
│  intercepts resp │  never blocks       │  /v1/events       │
│  extracts tokens │  batches every 1s   │  /api/analytics   │     cache    ┌────────────┐
│  calculates cost │                     │  /api/budgets     │ ──────────→ │   Redis    │
└─────────────────┘                     │  /api/projects    │             │  (port 6379)│
                                        └──────────────────┘             └────────────┘
                                                │
                                                │ REST API (JSON)
                                                ▼
                                        ┌──────────────────┐
                                        │  React Dashboard  │
                                        │  (port 5173/5174) │
                                        │  Vite + TailwindCSS│
                                        │  Recharts + RQuery│
                                        └──────────────────┘
```

## Data Flow

### 1. Event Ingestion (SDK → API → DB)
```
Developer Code
  → tokenbudget.wrap() patches client.chat.completions.create()
  → User makes normal OpenAI/Anthropic API call
  → SDK intercepts RESPONSE (not request) — zero latency impact
  → Extracts: model, input_tokens, output_tokens from response.usage
  → Calculates cost via local pricing table
  → Reads current tags from contextvars (feature, user_id, env, etc.)
  → Creates UsageEvent dataclass
  → Enqueues to thread-safe queue (never blocks caller)
  → Background daemon thread flushes every 1 second
  → POST /v1/events/batch with Bearer API key auth
  → API validates key, creates Event rows in PostgreSQL
  → Returns 202 Accepted
```

### 2. Dashboard Reads (Frontend → API → DB)
```
React Dashboard
  → React Query hook fires GET /api/analytics/summary?period=30d
  → Axios interceptor adds Bearer token from localStorage
  → API middleware validates API key, extracts user_id
  → Analytics service runs SQL aggregation on events table
  → Returns JSON: {total_cost_usd, total_requests, avg_cost_per_request, ...}
  → React Query caches result (staleTime: 60s)
  → Recharts renders line/pie/bar charts
```

### 3. Demo Mode (No API Needed)
```
User clicks "Try the live demo" on landing page
  → enableDemoMode() sets localStorage flags
  → React Query hooks check isDemoMode()
  → If true: return Promise.resolve(DEMO_DATA) instead of API call
  → Dashboard renders with realistic fake data
  → Yellow DemoBanner shown at top
```

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| SDK | Python | 3.10+ | Client wrapping, event extraction |
| SDK HTTP | httpx | 0.27+ | Async event posting |
| API Framework | FastAPI | 0.115+ | REST API server |
| ORM | SQLAlchemy | 2.0+ | Async database access |
| Database | PostgreSQL | 16 | Primary data store |
| Cache | Redis | 7 | Rate limiting, caching |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Auth | bcrypt | 4.0+ | API key hashing |
| Frontend | React | 18 | UI framework |
| Build | Vite | 5 | Dev server + bundler |
| Styling | TailwindCSS | 3.4 | Utility-first CSS |
| Charts | Recharts | 2.12 | Data visualization |
| Data Fetching | React Query | 5 | Server state management |
| Icons | Lucide React | 0.400 | Icon library |
| Routing | React Router | 6 | Client-side routing |
| Containers | Docker Compose | - | Local dev infrastructure |

## Security Model

### API Key Authentication
- Keys are prefixed `tb_ak_` + 32 random hex characters
- Raw keys are NEVER stored — only bcrypt hashes
- Keys are validated per-request via `require_api_key` FastAPI dependency
- Each key is scoped to a user and optionally a team + project

### Request Flow
```
Client Request
  → Authorization: Bearer tb_ak_xxxxxxxxxx
  → middleware/api_key_auth.py
  → Iterate all active keys for prefix match
  → bcrypt.verify(raw_key, stored_hash)
  → Return (ApiKey, User) or 401
```

### CORS
- Development: `allow_origins=["*"]`
- Production: Set `ALLOWED_ORIGINS` env var to specific domains

### Admin Endpoints
- `GET /api/waitlist` requires `X-Admin-Key` header matching `ADMIN_KEY` env var

---

## Session 2 — New Architecture Components

### OpenTelemetry Ingest Layer

```
OTel-Instrumented App
  → OTLP exporter sends traces to POST /v1/traces
  → OTel ingest router parses resourceSpans
  → Maps GenAI semantic convention attributes to UsageEvent fields
  → Reasoning tokens (gen_ai.usage.reasoning_tokens) tracked for o1/o3/o4-mini/Claude thinking
  → Events stored in PostgreSQL via existing event_service
  → Returns 202 Accepted with accepted/dropped counts
```

This allows any application instrumented with OpenTelemetry GenAI semantic conventions to send usage data to TokenBudget without the Python or JS SDK.

### Alert Dispatcher (Slack / Webhook)

```
Budget threshold crossed
  → alert_service.check_budget_thresholds() detects crossing
  → Creates Alert row in database
  → Dispatches to configured channels:
     ├── Slack: POST to incoming webhook URL with formatted message
     └── Webhook: POST to generic URL with JSON payload
  → Alert configurations managed via /api/alerts CRUD endpoints
  → Idempotent: same threshold on same budget never re-alerts
```

### Export Service

```
User requests export
  → GET /api/exports/csv or /api/exports/pdf
  → Export service queries events for the given period
  → CSV: streams rows as text/csv with all event fields including reasoning_tokens
  → PDF: generates summary report with model breakdown charts
  → Supports project_id filter for project-scoped exports
```

### Price Monitoring

```
Admin triggers POST /api/admin/sync-pricing
  → Fetches latest pricing data from LiteLLM pricing tables
  → Compares against stored pricing in local pricing table
  → Detects changes: new models, price increases/decreases
  → Stores price change records (queryable via GET /api/price-changes)
  → Updates local pricing table with new values
  → Returns sync summary with counts of updates and changes
```

### JavaScript/TypeScript SDK

```
JS/TS Application
  → npm install @tokenbudget/sdk
  → wrapOpenAI(client, config) patches openai client
  → wrapAnthropic(client, config) patches anthropic client
  → tags() context helper for feature/user tracking
  → Background fetch-based transport posts to /v1/events/batch
  → Same event schema as Python SDK (including reasoning_tokens)
```
