# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.pricing module."""
import pytest


def test_gpt4_cost_calculation():
    """GPT-4 cost calculation is correct."""
    from tokenbudget.pricing import calculate_cost
    # gpt-4: $30/1M input, $60/1M output
    cost = calculate_cost("gpt-4", input_tokens=1000, output_tokens=1000)
    assert cost > 0.0
    # 1000 input + 1000 output at gpt-4 rates
    expected = (1000 * 30 / 1_000_000) + (1000 * 60 / 1_000_000)
    assert abs(cost - expected) < 1e-9


def test_claude_cost_calculation():
    """Claude Sonnet cost calculation is correct."""
    from tokenbudget.pricing import calculate_cost
    cost = calculate_cost("claude-sonnet-4-20250514", input_tokens=1000, output_tokens=500)
    assert cost > 0.0


def test_unknown_model_returns_zero():
    """Unknown model returns 0.0 cost."""
    from tokenbudget.pricing import calculate_cost
    cost = calculate_cost("totally-unknown-model-xyz", input_tokens=1000, output_tokens=1000)
    assert cost == 0.0


def test_common_models_exist():
    """Common models are present in the pricing table."""
    from tokenbudget.pricing import PRICING
    expected_models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514",
        "claude-haiku-4-5-20251001",
    ]
    for model in expected_models:
        assert model in PRICING, f"Model {model!r} not found in PRICING"


def test_pricing_has_input_output_keys():
    """Each pricing entry has 'input' and 'output' keys."""
    from tokenbudget.pricing import PRICING
    for model, rates in PRICING.items():
        assert "input" in rates, f"Model {model!r} missing 'input' key"
        assert "output" in rates, f"Model {model!r} missing 'output' key"


def test_gpt4o_mini_cost():
    """GPT-4o-mini has a lower cost than GPT-4."""
    from tokenbudget.pricing import calculate_cost
    gpt4_cost = calculate_cost("gpt-4", input_tokens=1000, output_tokens=1000)
    mini_cost = calculate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=1000)
    assert mini_cost < gpt4_cost


def test_zero_tokens_returns_zero():
    """Zero tokens returns zero cost."""
    from tokenbudget.pricing import calculate_cost
    cost = calculate_cost("gpt-4", input_tokens=0, output_tokens=0)
    assert cost == 0.0


def test_claude_opus_cost():
    """Claude Opus cost calculation works."""
    from tokenbudget.pricing import calculate_cost
    cost = calculate_cost("claude-opus-4-20250514", input_tokens=500, output_tokens=500)
    assert cost > 0.0


def test_claude_haiku_cost():
    """Claude Haiku cost calculation works."""
    from tokenbudget.pricing import calculate_cost
    cost = calculate_cost("claude-haiku-4-5-20251001", input_tokens=500, output_tokens=500)
    assert cost > 0.0
