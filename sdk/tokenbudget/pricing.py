# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget pricing — per-token costs for known models."""

# Costs in USD per 1M tokens
PRICING: dict[str, dict[str, float]] = {
    # OpenAI models
    "gpt-4": {
        "input": 30.0,   # $30 / 1M tokens
        "output": 60.0,  # $60 / 1M tokens
    },
    "gpt-4-turbo": {
        "input": 10.0,
        "output": 30.0,
    },
    "gpt-4o": {
        "input": 2.5,
        "output": 10.0,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50,
    },
    # Anthropic models
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "output": 15.0,
    },
    "claude-opus-4-20250514": {
        "input": 15.0,
        "output": 75.0,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.0,
    },
    # AWS Bedrock models
    "anthropic.claude-3-5-sonnet": {
        "input": 3.0,
        "output": 15.0,
    },
    "anthropic.claude-3-haiku": {
        "input": 0.25,
        "output": 1.25,
    },
    "amazon.titan-text-express": {
        "input": 0.20,
        "output": 0.60,
    },
    "amazon.titan-text-lite": {
        "input": 0.15,
        "output": 0.20,
    },
    "meta.llama3-70b-instruct": {
        "input": 0.99,
        "output": 0.99,
    },
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for the given model and token counts.

    Returns 0.0 for unknown models.
    """
    rates = PRICING.get(model)
    if rates is None:
        return 0.0
    # Costs are per 1M tokens
    input_cost = (input_tokens * rates["input"]) / 1_000_000
    output_cost = (output_tokens * rates["output"]) / 1_000_000
    return input_cost + output_cost
