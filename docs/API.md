# TokenBudget API — Developer Documentation

## Overview

FastAPI backend serving REST endpoints for event ingestion, analytics, budget management, project organization, and API key management. Completely free and open source -- all endpoints are available to everyone with no plan restrictions. Async throughout using SQLAlchemy 2.0 + asyncpg.

## Running Locally

```bash
cd api
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Requires: PostgreSQL on `localhost:5432` and Redis on `localhost:6379` (via `docker compose up -d`).

---

## Project Structure

```
api/
├── app/
│   ├── main.py              # FastAPI app factory, CORS, router registration
│   ├── config.py             # Pydantic Settings (env vars)
│   ├── database.py           # SQLAlchemy async engine + session
│   ├── models/               # ORM models (1 file per table)
│   │   ├── base.py           # DeclarativeBase + TimestampMixin
│   │   ├── user.py           # User
│   │   ├── team.py           # Team + TeamMember
│   │   ├── project.py        # Project
│   │   ├── api_key.py        # ApiKey
│   │   ├── event.py          # Event (usage tracking)
│   │   ├── budget.py         # Budget
│   │   ├── alert.py          # Alert
│   │   ├── subscription.py   # Subscription (billing)
│   │   └── waitlist.py       # Waitlist
│   ├── schemas/              # Pydantic request/response models
│   │   ├── common.py         # ErrorResponse
│   │   ├── events.py         # EventCreate, EventBatch
│   │   ├── keys.py           # KeyCreate, KeyResponse, KeyCreateResponse
│   │   ├── budgets.py        # BudgetCreate, BudgetUpdate, BudgetResponse
│   │   ├── projects.py       # ProjectCreate, ProjectUpdate, ProjectResponse
│   │   └── analytics.py      # AnalyticsSummary, ModelBreakdown, etc.
│   ├── routers/              # FastAPI route handlers
│   │   ├── health.py         # GET /health
│   │   ├── events.py         # POST /v1/events, /v1/events/batch
│   │   ├── keys.py           # CRUD /api/keys
│   │   ├── budgets.py        # CRUD /api/budgets
│   │   ├── projects.py       # CRUD /api/projects + analytics
│   │   ├── analytics.py      # GET /api/analytics/*
│   │   ├── pricing.py        # GET /v1/pricing
│   │   └── waitlist.py       # POST/GET /api/waitlist
│   ├── services/             # Business logic (decoupled from routes)
│   │   ├── event_service.py
│   │   ├── key_service.py
│   │   ├── budget_service.py
│   │   ├── project_service.py
│   │   ├── analytics_service.py
│   │   └── alert_service.py
│   ├── middleware/
│   │   └── api_key_auth.py   # Bearer token validation
│   └── tasks/                # Background tasks (APScheduler)
│       └── scheduler.py
├── migrations/               # Alembic
│   ├── env.py
│   └── versions/             # 3 migration files
├── tests/                    # pytest async tests
└── pyproject.toml
```

---

## Database Schema

### Entity Relationship

```
users (1) ──→ (N) api_keys ──→ (N) events
  │                  │
  │                  └──→ projects (optional FK)
  │
  ├──→ (N) teams ──→ (N) team_members
  │         │
  │         └──→ (N) projects
  │
  └──→ (N) budgets ──→ (N) alerts
```

### Tables

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| clerk_id | VARCHAR | Unique, for Clerk auth mapping |
| email | VARCHAR | Unique |
| name | VARCHAR | |
| avatar_url | VARCHAR | Nullable |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

#### `teams`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | VARCHAR | |
| slug | VARCHAR | Unique |
| owner_id | UUID | FK → users |
| created_at / updated_at | TIMESTAMP | Auto |

#### `team_members`
| Column | Type | Notes |
|--------|------|-------|
| team_id | UUID | PK, FK → teams |
| user_id | UUID | PK, FK → users |
| role | ENUM | owner, admin, member |
| joined_at | TIMESTAMP | |

#### `projects`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| team_id | UUID | FK → teams, nullable |
| user_id | UUID | FK → users |
| name | VARCHAR | |
| slug | VARCHAR | Unique, auto-generated |
| description | VARCHAR | Nullable |
| color | VARCHAR | Hex color, default #6366f1 |
| is_active | BOOLEAN | Default true |
| created_at / updated_at | TIMESTAMP | Auto |

#### `api_keys`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| team_id | UUID | FK → teams, nullable |
| project_id | UUID | FK → projects, nullable |
| key_hash | VARCHAR | bcrypt hash (raw key never stored) |
| key_prefix | VARCHAR | First 8 chars for display |
| name | VARCHAR | User-friendly name |
| is_active | BOOLEAN | Revocable |
| created_at / updated_at | TIMESTAMP | Auto |

#### `events`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| api_key_id | UUID | FK → api_keys |
| user_id | UUID | FK → users |
| team_id | UUID | FK → teams, nullable |
| project_id | UUID | FK → projects, nullable |
| provider | VARCHAR | "openai", "anthropic" |
| model | VARCHAR | e.g., "gpt-4o" |
| input_tokens | INTEGER | |
| output_tokens | INTEGER | |
| total_tokens | INTEGER | |
| reasoning_tokens | INTEGER | Reasoning/thinking tokens (o1, o3, o4-mini, Claude thinking) |
| cost_usd | NUMERIC(10,6) | |
| latency_ms | INTEGER | |
| tags | JSONB | {"feature": "chatbot", ...} |
| metadata | JSONB | Additional context |
| created_at | TIMESTAMP | Indexed with team_id, user_id |

#### `budgets`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| team_id | UUID | FK → teams, nullable |
| user_id | UUID | FK → users |
| amount_usd | NUMERIC(10,2) | Budget limit |
| period | ENUM | daily, weekly, monthly |
| alert_thresholds | JSONB | [0.5, 0.8, 1.0] |
| is_active | BOOLEAN | |
| created_at / updated_at | TIMESTAMP | Auto |

#### `alerts`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| budget_id | UUID | FK → budgets |
| team_id | UUID | FK → teams (denormalized) |
| user_id | UUID | FK → users, nullable |
| type | ENUM | threshold_warning, budget_exceeded |
| threshold | NUMERIC(3,2) | Which threshold triggered |
| message | VARCHAR | Human-readable alert |
| notified_at | TIMESTAMP | When alert was created |
| channels | JSONB | ["email", "webhook"] |
| acknowledged_at | TIMESTAMP | Nullable |
| acknowledged_by | UUID | FK → users, nullable |

#### `waitlist`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| email | VARCHAR | Unique |
| source | VARCHAR | Default "landing" |
| created_at | TIMESTAMP | Auto |

---

## API Endpoints Reference

### Public Endpoints (No Auth)

#### `GET /health`
```json
{"status": "ok", "version": "0.2.0", "db": "connected", "redis": "connected"}
```

#### `GET /v1/pricing`
```json
{
  "models": {
    "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
    "gpt-4o": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    ...
  },
  "updated_at": "2026-03-19T00:00:00Z"
}
```

#### `POST /api/waitlist`
```json
// Request
{"email": "user@company.com", "source": "landing"}
// Response
{"message": "You're on the list! We'll be in touch.", "email": "user@company.com"}
```

#### `GET /api/waitlist` (Admin)
Requires `X-Admin-Key` header. Returns all waitlist entries.

---

### Event Ingestion (API Key Required)

#### `POST /v1/events` → 202
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "input_tokens": 150,
  "output_tokens": 50,
  "reasoning_tokens": 0,
  "total_tokens": 200,
  "cost_usd": 0.000875,
  "latency_ms": 1230,
  "tags": {"feature": "chatbot"},
  "metadata": {}
}
```

#### `POST /v1/events/batch` → 202
```json
{"events": [<EventCreate>, <EventCreate>, ...]}
```

---

### Analytics (API Key Required)

| Endpoint | Params | Returns |
|----------|--------|---------|
| `GET /api/analytics/summary` | `period=30d` | AnalyticsSummary |
| `GET /api/analytics/by-model` | `period=30d` | ModelBreakdown[] |
| `GET /api/analytics/by-user` | `period=30d` | UserBreakdown[] |
| `GET /api/analytics/timeseries` | `period=30d&granularity=daily` | TimeseriesPoint[] |
| `GET /api/analytics/by-tag` | `period=30d&tag_key=feature` | TagBreakdown[] |

Period format: `7d`, `30d`, `90d` (parsed to integer days).

---

### Budgets (API Key Required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/budgets` | Create budget |
| GET | `/api/budgets` | List all budgets |
| GET | `/api/budgets/{id}` | Get single budget |
| PUT | `/api/budgets/{id}` | Update budget |
| DELETE | `/api/budgets/{id}` | Delete budget |
| GET | `/api/budgets/{id}/status` | Current spend vs limit |

Budget response includes computed `current_spend_usd` and `utilization_pct`.

---

### Projects (API Key Required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects` | Create project (slug auto-generated) |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Get project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| GET | `/api/projects/{id}/analytics/summary` | Project-scoped summary |
| GET | `/api/projects/{id}/analytics/timeseries` | Project-scoped timeseries |
| GET | `/api/projects/{id}/keys` | Keys assigned to project |

---

### API Keys (API Key Required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/keys` | Create key → returns raw key ONCE |
| GET | `/api/keys` | List keys (prefix only, never raw) |
| DELETE | `/api/keys/{id}` | Revoke/deactivate key |

---

### OpenTelemetry Ingest (API Key Required)

#### `POST /v1/traces` → 202
Accepts OpenTelemetry OTLP trace data containing GenAI spans. This allows any OTel-instrumented application to send LLM usage data to TokenBudget without using the SDK.

```json
// Request — OTLP JSON format
{
  "resourceSpans": [
    {
      "resource": { "attributes": [...] },
      "scopeSpans": [
        {
          "spans": [
            {
              "name": "chat gpt-4o",
              "attributes": [
                { "key": "gen_ai.system", "value": { "stringValue": "openai" } },
                { "key": "gen_ai.request.model", "value": { "stringValue": "gpt-4o" } },
                { "key": "gen_ai.usage.prompt_tokens", "value": { "intValue": 150 } },
                { "key": "gen_ai.usage.completion_tokens", "value": { "intValue": 50 } },
                { "key": "gen_ai.usage.reasoning_tokens", "value": { "intValue": 0 } }
              ]
            }
          ]
        }
      ]
    }
  ]
}
// Response
{"accepted": 1, "dropped": 0}
```

The endpoint maps OTel GenAI semantic convention attributes to TokenBudget events. Unsupported span kinds are silently dropped.

---

### Alerts (API Key Required)

Manage alert configurations for Slack and generic webhook notifications.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/alerts` | Create alert configuration |
| GET | `/api/alerts` | List alert configurations |
| GET | `/api/alerts/{id}` | Get single alert configuration |
| DELETE | `/api/alerts/{id}` | Delete alert configuration |

#### `POST /api/alerts`
```json
// Request
{
  "name": "High spend alert",
  "type": "slack",
  "channel": "slack",
  "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
  "threshold_pct": 0.8,
  "budget_id": "uuid-of-budget"
}
// Response → 201
{
  "id": "uuid",
  "name": "High spend alert",
  "type": "slack",
  "channel": "slack",
  "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
  "threshold_pct": 0.8,
  "budget_id": "uuid-of-budget",
  "created_at": "2026-03-19T00:00:00Z"
}
```

Supported `channel` values: `"slack"` (Slack incoming webhook), `"webhook"` (generic HTTP POST).

---

### CSV / PDF Export (API Key Required)

#### `GET /api/exports/csv`
Export usage events as a CSV file.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `30d` | Time range (`7d`, `30d`, `90d`) |
| `project_id` | UUID | — | Optional project filter |

Returns `Content-Type: text/csv` with columns: `timestamp, provider, model, input_tokens, output_tokens, reasoning_tokens, total_tokens, cost_usd, latency_ms, tags`.

#### `GET /api/exports/pdf`
Export a usage summary report as a PDF file.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | string | `30d` | Time range (`7d`, `30d`, `90d`) |
| `project_id` | UUID | — | Optional project filter |

Returns `Content-Type: application/pdf` with a summary page and model breakdown chart.

---

### Price Changes (API Key Required)

#### `GET /api/price-changes`
Returns a list of detected model pricing changes.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `since` | ISO 8601 | 30 days ago | Only show changes after this date |
| `provider` | string | — | Filter by provider (`openai`, `anthropic`) |

```json
// Response
{
  "changes": [
    {
      "model": "gpt-4o",
      "provider": "openai",
      "field": "input_per_1k",
      "old_value": 0.005,
      "new_value": 0.0025,
      "detected_at": "2026-03-15T12:00:00Z"
    }
  ]
}
```

---

### Admin Endpoints

#### `POST /api/admin/sync-pricing`
Triggers a manual sync of model pricing from LiteLLM's pricing data. Requires `X-Admin-Key` header.

```json
// Response
{
  "status": "ok",
  "models_updated": 42,
  "new_models": 3,
  "price_changes_detected": 1,
  "synced_at": "2026-03-19T00:00:00Z"
}
```

---

## Services Layer

Each service encapsulates business logic, decoupled from HTTP routing.

### `event_service.py`
- `create_event(db, event_data, api_key)` → Event
- `create_events_batch(db, events, api_key)` → list[Event]

### `key_service.py`
- `generate_key()` → (raw_key, hash)
- `hash_key(raw_key)` → bcrypt hash
- `verify_key(raw_key, hashed)` → bool
- `create_api_key(db, user_id, name, team_id)` → (ApiKey, raw_key)
- `get_api_key_by_raw(db, raw_key)` → ApiKey | None

### `analytics_service.py`
- `get_summary(db, user_id, team_id, days)` → AnalyticsSummary
- `get_by_model(db, user_id, team_id, days)` → list[ModelBreakdown]
- `get_by_user(db, team_id, days)` → list[UserBreakdown]
- `get_timeseries(db, user_id, team_id, days, granularity)` → list[TimeseriesPoint]
- `get_by_tag(db, user_id, tag_key, team_id, days)` → list[TagBreakdown]

### `budget_service.py`
- `create_budget(db, user_id, data)` → Budget
- `get_budgets(db, user_id)` → list[Budget]
- `get_current_spend(db, user_id, period, team_id)` → float (uses `date_trunc`)
- `check_budget_thresholds(db, budget)` → list[Alert] (idempotent — skips already-alerted thresholds)

### `project_service.py`
- CRUD operations + `_slugify(name)` helper
- `get_project_analytics(db, project_id, days)` → AnalyticsSummary
- `get_project_timeseries(db, project_id, days)` → list[TimeseriesPoint]
- `get_project_keys(db, project_id)` → list[ApiKey]

### `alert_service.py`
- `create_alert(db, budget, threshold, alert_type)` → Alert
- `get_alerts(db, user_id, limit)` → list[Alert]

---

## Alembic Migrations

| Migration | Description |
|-----------|-------------|
| `20e35eadcde5` | Initial schema: users, teams, team_members, api_keys, events, budgets, alerts, subscriptions |
| `207aa2a0f0c6` | Add projects table; add project_id FK to api_keys and events |
| `38ef68bc6659` | Add waitlist table |

Run: `alembic upgrade head`
New migration: `alembic revision --autogenerate -m "description"`

---

## Test Coverage

| Test File | Count | Covers |
|-----------|-------|--------|
| test_health.py | 1 | Health endpoint |
| test_events.py | 4 | Event ingestion, auth, validation |
| test_keys.py | 3 | Key CRUD lifecycle |
| test_budgets.py | 10 | CRUD, thresholds, alerts, spend |
| test_analytics.py | 5 | Summary, models, timeseries |
| test_pricing.py | 6 | Pricing endpoint, model coverage |
| test_projects.py | 14 | CRUD, analytics, keys, slugs |
| test_waitlist.py | 3 | Join, dedup, admin auth |
| **Total** | **46** | |

Run: `cd api && pip install -e ".[dev]" && pytest -v`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://tokenbudget:localdev@localhost:5432/tokenbudget` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `CLERK_SECRET_KEY` | `""` | Clerk auth (future) |
| `ENVIRONMENT` | `development` | development/production |
| `ADMIN_KEY` | `change-this-admin-key` | Admin endpoint auth |
| `SLACK_WEBHOOK_URL` | `""` | Slack incoming webhook URL for alerts |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry trace ingest |
