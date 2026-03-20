# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Transparent proxy router — OpenAI & Anthropic.

Security contract
-----------------
* X-TokenBudget-Key is NEVER forwarded to upstream APIs.
* Authorization / x-api-key header values are NEVER logged or stored.
* If X-TokenBudget-Key is missing or invalid we still proxy the request
  but skip event recording.
* If the upstream returns an error we forward it unchanged and (if auth
  succeeded) record the event with error=True.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, engine
from app.lib.pricing import calculate_cost
from app.models.api_key import ApiKey
from app.models.event import Event
from app.services.key_service import get_api_key_by_raw

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["proxy"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OPENAI_BASE = "https://api.openai.com"
ANTHROPIC_BASE = "https://api.anthropic.com"

_PROXIED_BY_HEADER = {"X-Proxied-By": "TokenBudget/1.0"}

# Headers we must NEVER forward to upstream
_STRIP_REQUEST_HEADERS = {
    "x-tokenbudget-key",
    "x-tb-feature",
    "x-tb-user",
    "x-tb-project",
    "x-tb-tags",
    "host",
    "content-length",
    "transfer-encoding",
}


# ---------------------------------------------------------------------------
# Auth helper  (optional — fail-open)
# ---------------------------------------------------------------------------

async def _resolve_api_key(raw_key: str | None) -> ApiKey | None:
    """Validate a TokenBudget key.  Returns None if missing/invalid."""
    if not raw_key:
        return None
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            return await get_api_key_by_raw(session, raw_key)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Event recording  (fire-and-forget background task)
# ---------------------------------------------------------------------------

async def _record_event(
    *,
    api_key: ApiKey,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int | None,
    error: bool,
    feature: str | None,
    user_tag: str | None,
    project_tag: str | None,
    tags_raw: str | None,
) -> None:
    """Insert a proxy event row.  Swallows all exceptions — never blocks."""
    try:
        cost = calculate_cost(model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens

        tags: dict = {}
        if feature:
            tags["feature"] = feature
        if user_tag:
            tags["user"] = user_tag
        if project_tag:
            tags["project"] = project_tag
        if tags_raw:
            try:
                extra = json.loads(tags_raw)
                if isinstance(extra, dict):
                    tags.update(extra)
            except Exception:
                tags["raw_tags"] = tags_raw

        event = Event(
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            team_id=api_key.team_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            tags=tags if tags else None,
            metadata_={"proxy": True, "error": error},
        )

        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add(event)
            await session.commit()
    except Exception as exc:
        logger.warning("proxy: failed to record event: %s", exc)


# ---------------------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------------------

def _build_upstream_headers(request: Request, extra: dict | None = None) -> dict[str, str]:
    """Copy safe headers from the incoming request, stripping TB-specific ones."""
    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        if k.lower() not in _STRIP_REQUEST_HEADERS:
            headers[k] = v
    if extra:
        headers.update(extra)
    return headers


def _extract_tb_headers(request: Request) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Return (tb_key, feature, user, project, tags) from TB-specific headers."""
    tb_key = request.headers.get("x-tokenbudget-key") or request.headers.get("X-TokenBudget-Key")
    feature = request.headers.get("x-tb-feature")
    user = request.headers.get("x-tb-user")
    project = request.headers.get("x-tb-project")
    tags = request.headers.get("x-tb-tags")
    return tb_key, feature, user, project, tags


# ---------------------------------------------------------------------------
# Usage extraction
# ---------------------------------------------------------------------------

def _extract_openai_usage(body: dict) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def _extract_anthropic_usage(body: dict) -> tuple[int, int]:
    usage = body.get("usage") or {}
    return usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def _model_from_body(body: dict) -> str:
    return body.get("model") or "unknown"


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------

async def _stream_openai(
    upstream_response: httpx.Response,
) -> tuple[AsyncIterator[bytes], asyncio.Future]:
    """
    Yield SSE chunks as-is and capture usage from the last data chunk.
    Returns (async_iter, future_usage) where future_usage resolves to
    (input_tokens, output_tokens) after the stream ends.
    """
    loop = asyncio.get_event_loop()
    usage_future: asyncio.Future = loop.create_future()
    input_tokens = 0
    output_tokens = 0

    async def _gen() -> AsyncIterator[bytes]:
        nonlocal input_tokens, output_tokens
        try:
            async for chunk in upstream_response.aiter_bytes():
                yield chunk
                # Try to parse usage from each SSE data line
                try:
                    text = chunk.decode("utf-8", errors="ignore")
                    for line in text.splitlines():
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                            if payload and payload != "[DONE]":
                                obj = json.loads(payload)
                                u = obj.get("usage") or {}
                                if u.get("prompt_tokens"):
                                    input_tokens = u["prompt_tokens"]
                                if u.get("completion_tokens"):
                                    output_tokens = u["completion_tokens"]
                except Exception:
                    pass
        finally:
            if not usage_future.done():
                usage_future.set_result((input_tokens, output_tokens))

    return _gen(), usage_future


async def _stream_anthropic(
    upstream_response: httpx.Response,
) -> tuple[AsyncIterator[bytes], asyncio.Future]:
    loop = asyncio.get_event_loop()
    usage_future: asyncio.Future = loop.create_future()
    input_tokens = 0
    output_tokens = 0

    async def _gen() -> AsyncIterator[bytes]:
        nonlocal input_tokens, output_tokens
        try:
            async for chunk in upstream_response.aiter_bytes():
                yield chunk
                try:
                    text = chunk.decode("utf-8", errors="ignore")
                    for line in text.splitlines():
                        if line.startswith("data:"):
                            payload = line[5:].strip()
                            if payload:
                                obj = json.loads(payload)
                                u = obj.get("usage") or obj.get("message", {}).get("usage") or {}
                                if u.get("input_tokens"):
                                    input_tokens = u["input_tokens"]
                                if u.get("output_tokens"):
                                    output_tokens = u["output_tokens"]
                except Exception:
                    pass
        finally:
            if not usage_future.done():
                usage_future.set_result((input_tokens, output_tokens))

    return _gen(), usage_future


# ---------------------------------------------------------------------------
# Core proxy logic
# ---------------------------------------------------------------------------

async def _proxy(
    request: Request,
    background_tasks: BackgroundTasks,
    *,
    upstream_url: str,
    provider: str,
    usage_extractor,          # callable(dict) -> (int, int)
    stream_handler,           # coroutine(response) -> (gen, future)
    require_auth_header: str, # "authorization" or "x-api-key"
) -> Response:
    # 1. Extract TokenBudget headers
    tb_key, feature, user_tag, project_tag, tags_raw = _extract_tb_headers(request)

    # 2. Check upstream auth header present
    auth_val = request.headers.get(require_auth_header)
    if not auth_val:
        return Response(
            content=json.dumps({"error": f"Missing required header: {require_auth_header}"}),
            status_code=400,
            media_type="application/json",
        )

    # 3. Validate TB key (optional — fail-open)
    api_key: ApiKey | None = None
    if tb_key:
        api_key = await _resolve_api_key(tb_key)

    # 4. Read request body
    body_bytes = await request.body()
    try:
        body_dict = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        body_dict = {}

    is_stream = bool(body_dict.get("stream"))
    model = _model_from_body(body_dict)

    # 5. Build upstream headers (strip TB headers, keep everything else)
    upstream_headers = _build_upstream_headers(request)

    # 6. Forward to upstream
    start_ms = int(time.monotonic() * 1000)

    if is_stream:
        # ── Streaming path ──────────────────────────────────────────────
        async def _streaming_response() -> AsyncIterator[bytes]:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    request.method,
                    upstream_url,
                    headers=upstream_headers,
                    content=body_bytes,
                ) as upstream:
                    gen, usage_future = await stream_handler(upstream)
                    async for chunk in gen:
                        yield chunk

                    elapsed = int(time.monotonic() * 1000) - start_ms
                    in_tok, out_tok = await usage_future

                    if api_key is not None:
                        background_tasks.add_task(
                            _record_event,
                            api_key=api_key,
                            provider=provider,
                            model=model,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            latency_ms=elapsed,
                            error=upstream.status_code >= 400,
                            feature=feature,
                            user_tag=user_tag,
                            project_tag=project_tag,
                            tags_raw=tags_raw,
                        )

        return StreamingResponse(
            _streaming_response(),
            media_type="text/event-stream",
            headers=_PROXIED_BY_HEADER,
        )

    else:
        # ── Non-streaming path ───────────────────────────────────────────
        async with httpx.AsyncClient(timeout=120.0) as client:
            upstream_resp = await client.request(
                request.method,
                upstream_url,
                headers=upstream_headers,
                content=body_bytes,
            )

        elapsed = int(time.monotonic() * 1000) - start_ms
        error_flag = upstream_resp.status_code >= 400

        try:
            resp_body = upstream_resp.json()
        except Exception:
            resp_body = {}

        in_tok, out_tok = usage_extractor(resp_body)

        if api_key is not None:
            background_tasks.add_task(
                _record_event,
                api_key=api_key,
                provider=provider,
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                latency_ms=elapsed,
                error=error_flag,
                feature=feature,
                user_tag=user_tag,
                project_tag=project_tag,
                tags_raw=tags_raw,
            )

        response_headers = dict(_PROXIED_BY_HEADER)
        # Forward content-type from upstream
        ct = upstream_resp.headers.get("content-type", "application/json")
        response_headers["content-type"] = ct

        return Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=response_headers,
        )


# ---------------------------------------------------------------------------
# OpenAI endpoints
# ---------------------------------------------------------------------------

@router.post("/openai/v1/chat/completions")
async def proxy_openai_chat(request: Request, background_tasks: BackgroundTasks):
    return await _proxy(
        request,
        background_tasks,
        upstream_url=f"{OPENAI_BASE}/v1/chat/completions",
        provider="openai",
        usage_extractor=_extract_openai_usage,
        stream_handler=_stream_openai,
        require_auth_header="authorization",
    )


@router.post("/openai/v1/completions")
async def proxy_openai_completions(request: Request, background_tasks: BackgroundTasks):
    return await _proxy(
        request,
        background_tasks,
        upstream_url=f"{OPENAI_BASE}/v1/completions",
        provider="openai",
        usage_extractor=_extract_openai_usage,
        stream_handler=_stream_openai,
        require_auth_header="authorization",
    )


@router.post("/openai/v1/embeddings")
async def proxy_openai_embeddings(request: Request, background_tasks: BackgroundTasks):
    return await _proxy(
        request,
        background_tasks,
        upstream_url=f"{OPENAI_BASE}/v1/embeddings",
        provider="openai",
        usage_extractor=_extract_openai_usage,
        stream_handler=_stream_openai,
        require_auth_header="authorization",
    )


# ---------------------------------------------------------------------------
# Anthropic endpoint
# ---------------------------------------------------------------------------

@router.post("/anthropic/v1/messages")
async def proxy_anthropic_messages(request: Request, background_tasks: BackgroundTasks):
    return await _proxy(
        request,
        background_tasks,
        upstream_url=f"{ANTHROPIC_BASE}/v1/messages",
        provider="anthropic",
        usage_extractor=_extract_anthropic_usage,
        stream_handler=_stream_anthropic,
        require_auth_header="x-api-key",
    )
