// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { tags, tagsAsync, getCurrentTags } from '../src/context.js';

describe('context tags', () => {
  it('should return empty tags by default', () => {
    expect(getCurrentTags()).toEqual({});
  });

  it('should set tags within a sync context', () => {
    const result = tags({ feature: 'chat', userId: 'u_123' }, () => {
      const current = getCurrentTags();
      expect(current).toEqual({ feature: 'chat', userId: 'u_123' });
      return 'ok';
    });
    expect(result).toBe('ok');
  });

  it('should clear tags after the context exits', () => {
    tags({ feature: 'chat' }, () => {
      // inside
    });
    expect(getCurrentTags()).toEqual({});
  });

  it('should support nested tags with merging', () => {
    tags({ feature: 'chat', env: 'prod' }, () => {
      tags({ userId: 'u_123', env: 'staging' }, () => {
        const inner = getCurrentTags();
        expect(inner).toEqual({ feature: 'chat', env: 'staging', userId: 'u_123' });
      });
      const outer = getCurrentTags();
      expect(outer).toEqual({ feature: 'chat', env: 'prod' });
    });
  });

  it('should work with async functions', async () => {
    const result = await tagsAsync({ feature: 'summarize' }, async () => {
      const current = getCurrentTags();
      expect(current).toEqual({ feature: 'summarize' });
      return 42;
    });
    expect(result).toBe(42);
  });
});
