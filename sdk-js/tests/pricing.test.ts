// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { calculateCost } from '../src/pricing.js';

describe('calculateCost', () => {
  it('should calculate cost for gpt-4o', () => {
    // gpt-4o: $2.5/1M input, $10/1M output
    const cost = calculateCost('gpt-4o', 1000, 500);
    expect(cost).toBeCloseTo(0.0025 + 0.005, 6);
  });

  it('should calculate cost for gpt-4o-mini', () => {
    // gpt-4o-mini: $0.15/1M input, $0.60/1M output
    const cost = calculateCost('gpt-4o-mini', 1000000, 1000000);
    expect(cost).toBeCloseTo(0.15 + 0.60, 6);
  });

  it('should return 0 for unknown models', () => {
    const cost = calculateCost('unknown-model', 1000, 500);
    expect(cost).toBe(0);
  });

  it('should handle zero tokens', () => {
    const cost = calculateCost('gpt-4o', 0, 0);
    expect(cost).toBe(0);
  });
});
