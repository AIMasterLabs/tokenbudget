// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget SDK data types. */

/** A single usage event emitted after an LLM API call. */
export interface UsageEvent {
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  tags: Record<string, unknown>;
  metadata: Record<string, unknown>;
  timestamp: number;
}

/** Configuration options for the TokenBudget SDK. */
export interface TokenBudgetOptions {
  /** TokenBudget API key. Falls back to TOKENBUDGET_API_KEY env var. */
  apiKey?: string;
  /** Custom API endpoint. Defaults to https://api.tokenbudget.com */
  endpoint?: string;
  /** Whether tracking is enabled. Defaults to true. */
  enabled?: boolean;
  /** Flush interval in milliseconds. Defaults to 1000. */
  flushIntervalMs?: number;
  /** Maximum number of events to batch before flushing. Defaults to 10. */
  batchSize?: number;
  /** Maximum queue size before dropping events. Defaults to 1000. */
  maxQueueSize?: number;
}

/** Resolved (non-optional) configuration. */
export interface ResolvedConfig {
  apiKey: string;
  endpoint: string;
  enabled: boolean;
  flushIntervalMs: number;
  batchSize: number;
  maxQueueSize: number;
}

/** Per-model pricing rates in USD per 1M tokens. */
export interface ModelPricing {
  input: number;
  output: number;
}
