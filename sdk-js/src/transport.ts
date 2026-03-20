// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

/** TokenBudget event transport — batched delivery using fetch(). */

import type { UsageEvent, ResolvedConfig } from './types.js';

/**
 * Event transport that batches events and flushes them periodically.
 * Uses the built-in fetch() API (Node 18+ / browsers).
 * Never blocks the main thread — fire and forget.
 */
export class EventTransport {
  private queue: UsageEvent[] = [];
  private config: ResolvedConfig;
  private timer: ReturnType<typeof setInterval> | null = null;
  private stopped = false;

  constructor(config: ResolvedConfig) {
    this.config = config;
    this.startFlushTimer();
  }

  private startFlushTimer(): void {
    if (this.timer) return;
    this.timer = setInterval(() => {
      this.flush().catch(() => {
        // silently ignore flush errors
      });
    }, this.config.flushIntervalMs);

    // Allow Node.js to exit even if the timer is still running
    if (typeof this.timer === 'object' && 'unref' in this.timer) {
      this.timer.unref();
    }
  }

  /**
   * Enqueue an event. Never blocks, never throws.
   */
  send(event: UsageEvent): void {
    if (this.stopped) return;
    if (this.queue.length >= this.config.maxQueueSize) {
      // Drop the event — queue is full
      return;
    }
    this.queue.push(event);

    // Auto-flush if batch size reached
    if (this.queue.length >= this.config.batchSize) {
      this.flush().catch(() => {
        // silently ignore flush errors
      });
    }
  }

  /**
   * Flush all queued events to the API endpoint.
   */
  async flush(): Promise<void> {
    if (this.queue.length === 0) return;

    // Drain the queue into a local array
    const events = this.queue.splice(0);
    const url = `${this.config.endpoint}/v1/events/batch`;
    const payload = { events };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        // Re-queue events for retry
        this.requeue(events);
      }
    } catch {
      // Re-queue events for retry on next flush
      this.requeue(events);
    }
  }

  private requeue(events: UsageEvent[]): void {
    for (const event of events) {
      if (this.queue.length >= this.config.maxQueueSize) break;
      this.queue.push(event);
    }
  }

  /**
   * Stop the flush timer, flush remaining events, and clean up.
   */
  async shutdown(): Promise<void> {
    this.stopped = true;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    await this.flush();
  }

  /** Visible for testing. */
  get queueLength(): number {
    return this.queue.length;
  }
}
