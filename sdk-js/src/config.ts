// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget configuration resolver. */

import type { TokenBudgetOptions, ResolvedConfig } from './types.js';

/**
 * Resolve user-provided options into a complete configuration.
 * API key is resolved from: options.apiKey > TOKENBUDGET_API_KEY env var.
 */
export function resolveConfig(options: TokenBudgetOptions = {}): ResolvedConfig {
  const apiKey =
    options.apiKey ||
    (typeof process !== 'undefined' ? process.env?.TOKENBUDGET_API_KEY : undefined) ||
    '';

  if (!apiKey) {
    throw new Error(
      'apiKey is required. Pass it as an option or set the TOKENBUDGET_API_KEY environment variable.',
    );
  }

  return {
    apiKey,
    endpoint: options.endpoint || 'https://api.tokenbudget.com',
    enabled: options.enabled ?? true,
    flushIntervalMs: options.flushIntervalMs ?? 1000,
    batchSize: options.batchSize ?? 10,
    maxQueueSize: options.maxQueueSize ?? 1000,
  };
}
