# API Architecture Guide

A contributor-oriented guide to the TokenBudget API codebase. TokenBudget is completely free and open source -- there are no paid tiers or plan-gated features. Every contribution benefits the entire community.

---

## Three-layer pattern

Every feature follows the same layered structure:

```
Router  ->  Service  ->  Repository (SQLAlchemy model)
```

| Layer | Location | Responsibility |
|---|---|---|
| **Router** | `app/routers/<domain>.py` | HTTP interface: request validation, auth deps, response formatting |
| **Service** | `app/services/<domain>_service.py` | Business logic, orchestration, side-effects (alerts, events) |
| **Model** | `app/models/<domain>.py` | ORM definition, DB schema, simple query helpers |
| **Schema** | `app/schemas/<domain>.py` | Pydantic models for request/response validation |

---

## How to add a new endpoint

1. **Schema** — create or extend `app/schemas/<domain>.py` with request/response Pydantic models.
2. **Model** — if a new table is needed, add `app/models/<domain>.py` and register it in `app/models/__init__.py`.
3. **Service** — add `app/services/<domain>_service.py` with the business logic.
4. **Router** — add `app/routers/<domain>.py`, wire up the route, and include the router in `app/main.py`.
5. **Tests** — add `tests/test_<domain>.py` covering the happy path and key edge cases.

---

## How to add a new model

1. Create `app/models/<name>.py` with a SQLAlchemy model inheriting from `app.models.base.Base`.
2. Import and register the model in `app/models/__init__.py` so Alembic picks it up.
3. Generate an Alembic migration: `alembic revision --autogenerate -m "add <name> table"`.
4. Apply: `alembic upgrade head`.

---

## How to add a new AI provider

1. Add an entry to the `PROVIDERS` dict in `app/providers/__init__.py`:
   ```python
   "new_provider": {
   # replace <api.newprovider.com> with your api provider 
       "base_url": "https://<api.newprovider.com>", 
       "key_header": "Authorization",
   },
   ```
2. If the provider's auth or streaming format differs, extend the proxy logic in `app/routers/proxy.py`.
3. Add the provider's model pricing to `app/lib/pricing.py`.
4. Test with a real or mocked call through the proxy endpoint.

---

## How to add a new alert channel

1. Implement `send_<channel>(webhook_url, payload)` in `app/services/alert_dispatcher.py`.
2. Register the dotted path in `app/alerts/__init__.py`:
   ```python
   "<channel>": "app.services.alert_dispatcher.send_<channel>",
   ```
3. Add the channel name to the `AlertChannel` enum/choices if one exists in `app/models/alert_config.py`.
4. Write a test in `tests/` that mocks the external call and verifies dispatch.

---

## Testing conventions

- Tests live in `api/tests/`.
- Use `pytest` with `httpx.AsyncClient` for endpoint tests.
- Mock external services (Clerk, AI providers, Slack) — never make real network calls in tests.
- Run the full suite before opening a PR:
  ```bash
  python -m pytest tests/ -q
  ```
- Aim for at least one test per router endpoint covering the happy path.

---

## Welcome, contributors!

Whether you are fixing a typo, adding a new AI provider, or building an entire feature -- thank you. TokenBudget is a community project and every contribution matters. If you are unsure where to start, check the open issues on GitHub or ask in a discussion thread. We are happy to help you find a good first task.
