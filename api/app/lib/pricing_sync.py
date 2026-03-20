# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
LiteLLM pricing sync — fetches model pricing from the LiteLLM public repo
and updates the local pricing table.

Usage:
    # As a library call:
    from app.lib.pricing_sync import sync_from_litellm
    result = await sync_from_litellm()

    # As a CLI command:
    python -m app.lib.pricing_sync
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

# Providers we care about — only sync models from these providers
_SUPPORTED_PROVIDERS = {"openai", "anthropic", "google", "mistral", "cohere", "groq", "together"}


def _normalise_model_name(raw_name: str) -> str | None:
    """
    Extract a normalised model name from a LiteLLM key.

    LiteLLM keys look like "openai/gpt-4o" or just "gpt-4o".
    We strip the provider prefix if present.
    """
    if "/" in raw_name:
        parts = raw_name.split("/", 1)
        return parts[1].strip().lower()
    return raw_name.strip().lower()


def _parse_litellm_data(data: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """
    Parse LiteLLM pricing JSON into our pricing table format.

    Returns dict mapping model_name -> (input_per_1k, output_per_1k).
    LiteLLM prices are per-token; we convert to per-1k tokens.
    """
    pricing: dict[str, tuple[float, float]] = {}

    for raw_name, info in data.items():
        if not isinstance(info, dict):
            continue

        # Skip entries without pricing info
        input_cost = info.get("input_cost_per_token")
        output_cost = info.get("output_cost_per_token")
        if input_cost is None and output_cost is None:
            continue

        model_name = _normalise_model_name(raw_name)
        if not model_name:
            continue

        # Convert per-token to per-1k tokens
        input_per_1k = float(input_cost or 0) * 1000
        output_per_1k = float(output_cost or 0) * 1000

        # Deduplicate: prefer the first entry (usually the un-prefixed one)
        if model_name not in pricing:
            pricing[model_name] = (round(input_per_1k, 8), round(output_per_1k, 8))

    return pricing


async def sync_from_litellm(timeout: float = 30.0) -> dict[str, Any]:
    """
    Fetch model pricing from LiteLLM's public GitHub repo and return
    the parsed pricing table.

    Returns:
        {
            "models_fetched": int,
            "pricing": { "model-name": (input_per_1k, output_per_1k), ... }
        }
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(LITELLM_PRICING_URL)
        response.raise_for_status()

    data = response.json()
    pricing = _parse_litellm_data(data)

    logger.info("LiteLLM pricing sync: fetched %d models", len(pricing))
    return {
        "models_fetched": len(pricing),
        "pricing": pricing,
    }


def generate_pricing_snippet(pricing: dict[str, tuple[float, float]]) -> str:
    """
    Generate a Python dict literal that can be pasted into pricing.py.
    """
    lines = ["_PRICING: dict[str, tuple[float, float]] = {"]
    for model in sorted(pricing.keys()):
        inp, out = pricing[model]
        lines.append(f'    "{model}": ({inp}, {out}),')
    lines.append("}")
    return "\n".join(lines)


# ── CLI entry point ────────────────────────────────────────────────────────

async def _main() -> None:
    result = await sync_from_litellm()
    print(f"Fetched pricing for {result['models_fetched']} models")
    print()
    # Print a subset for preview
    count = 0
    for model, (inp, out) in sorted(result["pricing"].items()):
        print(f"  {model:40s}  input={inp:.6f}/1k  output={out:.6f}/1k")
        count += 1
        if count >= 30:
            print(f"  ... and {len(result['pricing']) - 30} more")
            break


if __name__ == "__main__":
    asyncio.run(_main())
