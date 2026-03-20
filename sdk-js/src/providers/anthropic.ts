// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** Anthropic provider integration — wraps the Anthropic client to track usage. */

import type { UsageEvent, TokenBudgetOptions } from '../types.js';
import { resolveConfig } from '../config.js';
import { calculateCost } from '../pricing.js';
import { getCurrentTags } from '../context.js';
import { EventTransport } from '../transport.js';

// Shared transport instance
let _transport: EventTransport | null = null;

/**
 * Wrap an Anthropic client to automatically track token usage.
 *
 * Patches `client.messages.create` in-place and returns the same client.
 *
 * @param client - An Anthropic client instance
 * @param options - TokenBudget configuration options
 * @returns The same client, now patched to track usage
 */
export function wrapAnthropic<T extends Record<string, any>>(
  client: T,
  options: TokenBudgetOptions = {},
): T {
  const config = resolveConfig(options);

  if (!config.enabled) return client;

  if (!_transport) {
    _transport = new EventTransport(config);
  }

  const transport = _transport;
  const messages = client.messages as Record<string, any>;

  if (!messages?.create) {
    throw new Error(
      'TokenBudget: client.messages.create not found. Pass an Anthropic client instance.',
    );
  }

  const originalCreate = messages.create.bind(messages);

  messages.create = async function patchedCreate(
    ...args: any[]
  ): Promise<any> {
    const start = performance.now();
    const response = await originalCreate(...args);
    const elapsedMs = Math.round(performance.now() - start);

    try {
      const model: string = response.model ?? 'unknown';
      const usage = response.usage;
      const inputTokens: number = usage?.input_tokens ?? 0;
      const outputTokens: number = usage?.output_tokens ?? 0;
      const totalTokens = inputTokens + outputTokens;
      const costUsd = calculateCost(model, inputTokens, outputTokens);
      const tags = getCurrentTags();

      const event: UsageEvent = {
        provider: 'anthropic',
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

/** Flush and shut down the Anthropic transport. Exported for testing. */
export async function _shutdownAnthropic(): Promise<void> {
  if (_transport) {
    await _transport.shutdown();
    _transport = null;
  }
}

/** Reset the shared transport. Exported for testing. */
export function _resetAnthropic(): void {
  _transport = null;
}
