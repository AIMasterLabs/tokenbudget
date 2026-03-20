// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget pricing — per-token costs for known models. */

import type { ModelPricing } from './types.js';

/** Costs in USD per 1M tokens. */
const PRICING: Record<string, ModelPricing> = {
  // OpenAI models
  'gpt-4': { input: 30.0, output: 60.0 },
  'gpt-4-turbo': { input: 10.0, output: 30.0 },
  'gpt-4o': { input: 2.5, output: 10.0 },
  'gpt-4o-mini': { input: 0.15, output: 0.60 },
  'gpt-3.5-turbo': { input: 0.50, output: 1.50 },
  // Anthropic models
  'claude-sonnet-4-20250514': { input: 3.0, output: 15.0 },
  'claude-opus-4-20250514': { input: 15.0, output: 75.0 },
  'claude-haiku-4-5-20251001': { input: 0.80, output: 4.0 },
};

/**
 * Calculate cost in USD for the given model and token counts.
 * Returns 0.0 for unknown models.
 */
export function calculateCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
): number {
  const rates = PRICING[model];
  if (!rates) return 0.0;
  const inputCost = (inputTokens * rates.input) / 1_000_000;
  const outputCost = (outputTokens * rates.output) / 1_000_000;
  return inputCost + outputCost;
}
