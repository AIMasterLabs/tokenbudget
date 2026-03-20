// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget context management — tags for feature/user attribution. */

// In Node.js we use AsyncLocalStorage for context propagation.
// In browsers, we fall back to a simple global stack.

import { AsyncLocalStorage } from 'node:async_hooks';

type Tags = Record<string, unknown>;

const storage = new AsyncLocalStorage<Tags>();

/**
 * Return the current context tags (empty object if none set).
 */
export function getCurrentTags(): Tags {
  return { ...(storage.getStore() ?? {}) };
}

/**
 * Run a function with the given tags set as context.
 * Supports nesting: inner tags merge with (and override) outer tags.
 */
export function tags<T>(tagValues: Tags, fn: () => T): T {
  const outer = storage.getStore() ?? {};
  const merged = { ...outer, ...tagValues };
  return storage.run(merged, fn);
}

/**
 * Async version of tags() for async functions.
 */
export async function tagsAsync<T>(tagValues: Tags, fn: () => Promise<T>): Promise<T> {
  const outer = storage.getStore() ?? {};
  const merged = { ...outer, ...tagValues };
  return storage.run(merged, fn);
}
