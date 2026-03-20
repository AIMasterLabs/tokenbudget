// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { EventTransport } from '../src/transport.js';
import type { ResolvedConfig, UsageEvent } from '../src/types.js';

function makeConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
  return {
    apiKey: 'tb_ak_test',
    endpoint: 'https://api.tokenbudget.com',
    enabled: true,
    flushIntervalMs: 60000, // long interval to prevent auto-flush in tests
    batchSize: 100,
    maxQueueSize: 1000,
    ...overrides,
  };
}

function makeEvent(overrides: Partial<UsageEvent> = {}): UsageEvent {
  return {
    provider: 'openai',
    model: 'gpt-4o',
    input_tokens: 100,
    output_tokens: 50,
    total_tokens: 150,
    cost_usd: 0.00075,
    latency_ms: 200,
    tags: {},
    metadata: {},
    timestamp: Date.now() / 1000,
    ...overrides,
  };
}

describe('EventTransport', () => {
  let transport: EventTransport;

  afterEach(async () => {
    if (transport) {
      await transport.shutdown();
    }
  });

  it('should queue events', () => {
    transport = new EventTransport(makeConfig());
    transport.send(makeEvent());
    transport.send(makeEvent());
    expect(transport.queueLength).toBe(2);
  });

  it('should drop events when queue is full', () => {
    transport = new EventTransport(makeConfig({ maxQueueSize: 2 }));
    transport.send(makeEvent());
    transport.send(makeEvent());
    transport.send(makeEvent()); // should be dropped
    expect(transport.queueLength).toBe(2);
  });

  it('should auto-flush when batchSize reached', async () => {
    const fetches: { url: string; body: string }[] = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (input: any, init: any) => {
      fetches.push({ url: String(input), body: init?.body });
      return new Response('{"ok":true}', { status: 200 });
    };

    try {
      transport = new EventTransport(makeConfig({ batchSize: 2 }));
      transport.send(makeEvent());
      transport.send(makeEvent()); // should trigger flush

      // Allow the async flush to complete
      await new Promise((r) => setTimeout(r, 50));

      expect(fetches.length).toBe(1);
      expect(fetches[0].url).toBe('https://api.tokenbudget.com/v1/events/batch');
      const body = JSON.parse(fetches[0].body);
      expect(body.events).toHaveLength(2);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('should send correct authorization header', async () => {
    let capturedHeaders: Record<string, string> = {};
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (_input: any, init: any) => {
      capturedHeaders = init?.headers ?? {};
      return new Response('{"ok":true}', { status: 200 });
    };

    try {
      transport = new EventTransport(makeConfig({ apiKey: 'tb_ak_secret' }));
      transport.send(makeEvent());
      await transport.flush();
      expect(capturedHeaders['Authorization']).toBe('Bearer tb_ak_secret');
      expect(capturedHeaders['Content-Type']).toBe('application/json');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('should re-queue events on fetch failure', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => {
      throw new Error('Network error');
    };

    try {
      transport = new EventTransport(makeConfig());
      transport.send(makeEvent());
      transport.send(makeEvent());
      expect(transport.queueLength).toBe(2);

      await transport.flush();

      // Events should be re-queued
      expect(transport.queueLength).toBe(2);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
