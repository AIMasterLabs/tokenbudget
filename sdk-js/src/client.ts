// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget public client API. */

import type { UsageEvent, TokenBudgetOptions } from './types.js';
import { resolveConfig } from './config.js';
import { EventTransport } from './transport.js';
import { getCurrentTags } from './context.js';
import { calculateCost } from './pricing.js';

// Module-level singleton transport
let _transport: EventTransport | null = null;

/**
 * Configure the global TokenBudget transport.
 * Call this once at startup if you want to use `track()` directly.
 */
export function configure(options: TokenBudgetOptions = {}): void {
  const config = resolveConfig(options);
  _transport = new EventTransport(config);
}

/**
 * Manually track a usage event.
 * Requires `configure()` to have been called first.
 */
export function track(event: Omit<UsageEvent, 'tags' | 'metadata' | 'timestamp'> & {
  tags?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}): void {
  if (!_transport) {
    throw new Error('TokenBudget: call configure() before track().');
  }

  const fullEvent: UsageEvent = {
    ...event,
    tags: { ...getCurrentTags(), ...(event.tags ?? {}) },
    metadata: event.metadata ?? {},
    timestamp: Date.now() / 1000,
  };

  _transport.send(fullEvent);
}

/**
 * Flush remaining events and shut down the global transport.
 */
export async function shutdown(): Promise<void> {
  if (_transport) {
    await _transport.shutdown();
    _transport = null;
  }
}
