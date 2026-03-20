// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { resolveConfig } from '../src/config.js';

describe('resolveConfig', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.TOKENBUDGET_API_KEY;
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it('should resolve with explicit apiKey', () => {
    const config = resolveConfig({ apiKey: 'tb_ak_test123' });
    expect(config.apiKey).toBe('tb_ak_test123');
    expect(config.endpoint).toBe('https://api.tokenbudget.com');
    expect(config.enabled).toBe(true);
    expect(config.flushIntervalMs).toBe(1000);
    expect(config.batchSize).toBe(10);
    expect(config.maxQueueSize).toBe(1000);
  });

  it('should resolve apiKey from environment variable', () => {
    process.env.TOKENBUDGET_API_KEY = 'tb_ak_fromenv';
    const config = resolveConfig();
    expect(config.apiKey).toBe('tb_ak_fromenv');
  });

  it('should throw when no apiKey is provided', () => {
    expect(() => resolveConfig()).toThrow('apiKey is required');
  });

  it('should allow custom endpoint', () => {
    const config = resolveConfig({
      apiKey: 'tb_ak_test',
      endpoint: 'https://custom.example.com',
    });
    expect(config.endpoint).toBe('https://custom.example.com');
  });

  it('should allow disabling tracking', () => {
    const config = resolveConfig({ apiKey: 'tb_ak_test', enabled: false });
    expect(config.enabled).toBe(false);
  });

  it('should allow custom flush interval and batch size', () => {
    const config = resolveConfig({
      apiKey: 'tb_ak_test',
      flushIntervalMs: 5000,
      batchSize: 50,
    });
    expect(config.flushIntervalMs).toBe(5000);
    expect(config.batchSize).toBe(50);
  });
});
