# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
OpenTelemetry OTLP trace ingest router.

Accepts OTLP JSON (and protobuf) trace exports, extracts GenAI semantic
convention spans, and converts them into TokenBudget events.

Auth contract (same as proxy):
- X-TokenBudget-Key header is used for authentication.
- If missing or invalid, we still accept the request but skip event recording.
- Never break the customer's instrumentation pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.lib.pricing import calculate_cost
from app.models.event import Event
from app.services.key_service import get_api_key_by_raw

logger = logging.getLogger(__name__)

router = APIRouter(tags=["otlp"])

# ---------------------------------------------------------------------------
# GenAI semantic convention attribute keys
# https://opentelemetry.io/docs/specs/semconv/gen-ai/
# ---------------------------------------------------------------------------
_ATTR_SYSTEM = "gen_ai.system"
_ATTR_MODEL = "gen_ai.request.model"
_ATTR_INPUT_TOKENS = "gen_ai.usage.input_tokens"
_ATTR_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
_ATTR_COST = "gen_ai.usage.cost"

# Map OTel gen_ai.system values to TokenBudget provider names
_SYSTEM_TO_PROVIDER: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "mistral": "mistral",
    "cohere": "cohere",
    "meta": "meta",
    "amazon": "amazon",
    "azure": "azure",
    "groq": "groq",
    "together": "together",
}


def _extract_attributes(span: dict[str, Any]) -> dict[str, Any]:
    """Flatten OTel span attributes list into a simple dict."""
    attrs: dict[str, Any] = {}
    for attr in span.get("attributes", []):
        key = attr.get("key", "")
        value = attr.get("value", {})
        # OTel JSON encodes values as {stringValue: ...}, {intValue: ...}, etc.
        if "stringValue" in value:
            attrs[key] = value["stringValue"]
        elif "intValue" in value:
            attrs[key] = int(value["intValue"])
        elif "doubleValue" in value:
            attrs[key] = float(value["doubleValue"])
        elif "boolValue" in value:
            attrs[key] = value["boolValue"]
        else:
            # Fallback: try to get any value
            for v in value.values():
                attrs[key] = v
                break
    return attrs


def _is_genai_span(attrs: dict[str, Any]) -> bool:
    """Return True if the span has GenAI semantic convention attributes."""
    return _ATTR_SYSTEM in attrs or _ATTR_MODEL in attrs


def _parse_genai_span(span: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a GenAI span into a dict suitable for creating an Event."""
    system = attrs.get(_ATTR_SYSTEM, "other")
    provider = _SYSTEM_TO_PROVIDER.get(system, "other")
    model = attrs.get(_ATTR_MODEL, "unknown")

    input_tokens = int(attrs.get(_ATTR_INPUT_TOKENS, 0))
    output_tokens = int(attrs.get(_ATTR_OUTPUT_TOKENS, 0))
    total_tokens = input_tokens + output_tokens

    # Use provided cost or calculate from pricing table
    if _ATTR_COST in attrs:
        cost_usd = float(attrs[_ATTR_COST])
    else:
        cost_usd = calculate_cost(model, input_tokens, output_tokens)

    # Extract latency from span timestamps if available
    latency_ms = None
    start_ns = span.get("startTimeUnixNano")
    end_ns = span.get("endTimeUnixNano")
    if start_ns and end_ns:
        try:
            latency_ms = int((int(end_ns) - int(start_ns)) / 1_000_000)
        except (ValueError, TypeError):
            pass

    return {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "metadata": {
            "source": "otlp",
            "span_name": span.get("name", ""),
            "trace_id": span.get("traceId", ""),
            "span_id": span.get("spanId", ""),
        },
    }


def _extract_spans_from_otlp_json(body: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse OTLP JSON ExportTraceServiceRequest and return GenAI event dicts.

    Structure: { resourceSpans: [{ scopeSpans: [{ spans: [...] }] }] }
    """
    events: list[dict[str, Any]] = []
    for resource_span in body.get("resourceSpans", []):
        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                attrs = _extract_attributes(span)
                if _is_genai_span(attrs):
                    event = _parse_genai_span(span, attrs)
                    if event is not None:
                        events.append(event)
    return events


@router.post("/v1/traces", status_code=status.HTTP_200_OK)
async def ingest_traces(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Accept OTLP trace data (JSON format), extract GenAI spans,
    and convert them to TokenBudget events.
    """
    # ── Auth (best-effort, same as proxy) ────────────────────────────────
    tb_key = request.headers.get("X-TokenBudget-Key")
    api_key = None

    if tb_key:
        api_key = await get_api_key_by_raw(db, tb_key)

    # ── Parse body ───────────────────────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        # If we can't parse JSON, return 200 anyway (never break customer)
        logger.warning("OTLP ingest: failed to parse request body")
        return {"accepted": 0, "error": "invalid request body"}

    genai_events = _extract_spans_from_otlp_json(body)

    if not genai_events:
        return {"accepted": 0}

    # ── Persist events if authenticated ──────────────────────────────────
    if api_key is None:
        # No valid auth — accept the data but don't persist
        logger.info("OTLP ingest: no valid API key, skipping %d events", len(genai_events))
        return {"accepted": len(genai_events), "persisted": False}

    for evt in genai_events:
        event = Event(
            api_key_id=api_key.id,
            user_id=api_key.user_id,
            team_id=api_key.team_id,
            provider=evt["provider"],
            model=evt["model"],
            input_tokens=evt["input_tokens"],
            output_tokens=evt["output_tokens"],
            total_tokens=evt["total_tokens"],
            cost_usd=evt["cost_usd"],
            latency_ms=evt["latency_ms"],
            metadata_=evt.get("metadata"),
        )
        db.add(event)
    await db.commit()

    return {"accepted": len(genai_events), "persisted": True}
