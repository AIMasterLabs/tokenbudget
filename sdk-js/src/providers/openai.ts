// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** OpenAI provider integration — wraps the OpenAI client to track usage. */

import type { UsageEvent, TokenBudgetOptions } from '../types.js';
import { resolveConfig } from '../config.js';
import { calculateCost } from '../pricing.js';
import { getCurrentTags } from '../context.js';
import { EventTransport } from '../transport.js';

// Shared transport instance
let _transport: EventTransport | null = null;

/**
 * Wrap an OpenAI client to automatically track token usage.
 *
 * Patches `client.chat.completions.create` in-place and returns the same client.
 *
 * @param client - An OpenAI client instance
 * @param options - TokenBudget configuration options
 * @returns The same client, now patched to track usage
 */
export function wrapOpenAI<T extends Record<string, any>>(
  client: T,
  options: TokenBudgetOptions = {},
): T {
  const config = resolveConfig(options);

  if (!config.enabled) return client;

  if (!_transport) {
    _transport = new EventTransport(config);
  }

  const transport = _transport;
  const chat = client.chat as Record<string, any>;
  const completions = chat?.completions as Record<string, any>;

  if (!completions?.create) {
    throw new Error(
      'TokenBudget: client.chat.completions.create not found. Pass an OpenAI client instance.',
    );
  }

  const originalCreate = completions.create.bind(completions);

  completions.create = async function patchedCreate(
    ...args: any[]
  ): Promise<any> {
    const start = performance.now();
    const response = await originalCreate(...args);
    const elapsedMs = Math.round(performance.now() - start);

    try {
      const model: string = response.model ?? 'unknown';
      const usage = response.usage;
      const inputTokens: number = usage?.prompt_tokens ?? 0;
      const outputTokens: number = usage?.completion_tokens ?? 0;
      const totalTokens = inputTokens + outputTokens;
      const costUsd = calculateCost(model, inputTokens, outputTokens);
      const tags = getCurrentTags();

      const event: UsageEvent = {
        provider: 'openai',
        model,
        input_tokens: inputTokens,
        output_tokens: outputTokens,
        total_tokens: totalTokens,
        cost_usd: costUsd,
        latency_ms: elapsedMs,
        tags,
        metadata: {},
        timestamp: Date.now() / 1000,
      };

      transport.send(event);
    } catch {
      // Never let tracking errors affect the user
    }

    return response;
  };

  return client;
}

/** Flush and shut down the OpenAI transport. Exported for testing. */
export async function _shutdownOpenAI(): Promise<void> {
  if (_transport) {
    await _transport.shutdown();
    _transport = null;
  }
}

/** Reset the shared transport. Exported for testing. */
export function _resetOpenAI(): void {
  _transport = null;
}
