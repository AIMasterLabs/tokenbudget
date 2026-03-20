# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Built-in pricing table with fuzzy model matching.

Prices are per 1,000 tokens (input_per_1k, output_per_1k) in USD.
Fuzzy matching uses longest-prefix: "gpt-4o-2024-11-20" → "gpt-4o".
Unknown models return 0.0 cost (tokens are still tracked).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Pricing table  (input_per_1k, output_per_1k)  in USD
# ---------------------------------------------------------------------------
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o":                  (0.0025,   0.010),
    "gpt-4o-mini":             (0.00015,  0.0006),
    "gpt-4-turbo":             (0.01,     0.03),
    "gpt-4":                   (0.03,     0.06),
    "gpt-3.5-turbo":           (0.0005,   0.0015),
    "o1":                      (0.015,    0.060),
    "o3":                      (0.010,    0.040),
    "o3-mini":                 (0.0011,   0.0044),
    "o4-mini":                 (0.0011,   0.0044),
    "text-embedding-3-small":  (0.00002,  0.0),
    "text-embedding-3-large":  (0.00013,  0.0),
    "claude-opus-4":           (0.015,    0.075),
    "claude-sonnet-4":         (0.003,    0.015),
    "claude-haiku-4":          (0.00025,  0.00125),
    "claude-3-5-sonnet":       (0.003,    0.015),
    "claude-3-5-haiku":        (0.0008,   0.004),
}

# Models where reasoning tokens are billed at the output token rate
_REASONING_AS_OUTPUT: set[str] = {"o1", "o3", "o3-mini", "o4-mini"}

# Claude models bill thinking tokens at output rate
_CLAUDE_THINKING: set[str] = {
    "claude-opus-4", "claude-sonnet-4", "claude-haiku-4",
    "claude-3-5-sonnet", "claude-3-5-haiku",
}

# Pre-sort by key length descending so that more-specific prefixes match first
# (e.g. "gpt-4o-mini" before "gpt-4o" before "gpt-4").
_SORTED_KEYS: list[str] = sorted(_PRICING.keys(), key=len, reverse=True)


def _match_model(model: str) -> str | None:
    """
    Return the best-matching pricing key for *model*, or None if unknown.

    Strategy: normalise to lower-case then find the longest pricing key that
    is a prefix of the given model string.  This means:
      - exact match:            "gpt-4o"              → "gpt-4o"
      - versioned suffix:       "gpt-4o-2024-11-20"   → "gpt-4o"
      - mini takes priority:    "gpt-4o-mini-..."      → "gpt-4o-mini"
    """
    normalised = model.strip().lower()
    for key in _SORTED_KEYS:
        if normalised == key or normalised.startswith(key + "-") or normalised.startswith(key + ":"):
            return key
        # Also accept exact case-insensitive match without suffix separator
        if normalised == key:
            return key
    return None


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int = 0,
) -> float:
    """
    Calculate the USD cost for a model call.

    For reasoning models (o1, o3, o3-mini, o4-mini) and Claude models with
    thinking tokens, reasoning_tokens are billed at the output token rate.

    Returns 0.0 for unknown models (tokens are still tracked by the caller).
    """
    key = _match_model(model)
    if key is None:
        return 0.0
    input_per_1k, output_per_1k = _PRICING[key]
    cost = (input_tokens / 1000.0) * input_per_1k + (output_tokens / 1000.0) * output_per_1k

    # Add reasoning/thinking token cost at the output rate
    if reasoning_tokens > 0 and key in (_REASONING_AS_OUTPUT | _CLAUDE_THINKING):
        cost += (reasoning_tokens / 1000.0) * output_per_1k

    return round(cost, 8)
