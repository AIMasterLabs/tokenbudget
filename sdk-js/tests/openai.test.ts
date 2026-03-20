// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { wrapOpenAI, _resetOpenAI } from '../src/providers/openai.js';

describe('wrapOpenAI', () => {
  beforeEach(() => {
    _resetOpenAI();
    // Mock fetch globally
    globalThis.fetch = async () => new Response('{"ok":true}', { status: 200 });
  });

  it('should patch client.chat.completions.create', async () => {
    const mockResponse = {
      model: 'gpt-4o',
      usage: {
        prompt_tokens: 10,
        completion_tokens: 20,
        total_tokens: 30,
      },
      choices: [{ message: { content: 'Hello!' } }],
    };

    const fakeClient = {
      chat: {
        completions: {
          create: async () => mockResponse,
        },
      },
    };

    const wrapped = wrapOpenAI(fakeClient as any, { apiKey: 'tb_ak_test' });

    // Should return the same client object
    expect(wrapped).toBe(fakeClient);

    // Should still return the correct response
    const response = await wrapped.chat.completions.create({
      model: 'gpt-4o',
      messages: [{ role: 'user', content: 'Hi' }],
    });
    expect(response.model).toBe('gpt-4o');
    expect(response.usage.prompt_tokens).toBe(10);
  });

  it('should throw if client has no chat.completions.create', () => {
    expect(() => wrapOpenAI({} as any, { apiKey: 'tb_ak_test' })).toThrow(
      'client.chat.completions.create not found',
    );
  });

  it('should not patch when enabled is false', () => {
    const originalCreate = async () => ({});
    const fakeClient = {
      chat: {
        completions: {
          create: originalCreate,
        },
      },
    };

    wrapOpenAI(fakeClient as any, { apiKey: 'tb_ak_test', enabled: false });
    expect(fakeClient.chat.completions.create).toBe(originalCreate);
  });
});
