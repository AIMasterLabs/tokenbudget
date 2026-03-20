// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'

const installCode = `pip install tokenbudget`

const usageCode = `import openai
from tokenbudget import TokenBudgetTracker

# Wrap your OpenAI client
tracker = TokenBudgetTracker(api_key="tb_your_key_here")
client = tracker.wrap(openai.OpenAI())

# Use as normal — usage is tracked automatically
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
`

const sdkCode = `# Or use the low-level SDK directly
from tokenbudget import TokenBudget

tb = TokenBudget(api_key="tb_your_key_here")
tb.track(
    model="gpt-4o",
    input_tokens=150,
    output_tokens=42,
    latency_ms=320,
    user_id="user_123",  # optional
)
`

function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  return (
    <pre className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-4 overflow-x-auto text-xs text-[#e2e8f0] leading-relaxed">
      <code className={`language-${language}`}>{code.trim()}</code>
    </pre>
  )
}

export function Settings() {
  return (
    <div className="flex flex-col min-h-full">
      <Header title="Settings" />

      <div className="p-6 flex flex-col gap-6 max-w-3xl">
        {/* SDK Installation */}
        <Card title="SDK Installation">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-[#64748b]">
              Install the TokenBudget Python SDK to start tracking your AI usage:
            </p>
            <CodeBlock code={installCode} language="bash" />
          </div>
        </Card>

        {/* Auto-track with wrap */}
        <Card title="Auto-track with Client Wrapping">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-[#64748b]">
              The easiest way to get started — wrap your existing OpenAI client and all requests
              are tracked automatically:
            </p>
            <CodeBlock code={usageCode} />
          </div>
        </Card>

        {/* Manual tracking */}
        <Card title="Manual Event Tracking">
          <div className="flex flex-col gap-4">
            <p className="text-sm text-[#64748b]">
              For custom integrations or non-OpenAI models, use the low-level SDK to track events
              directly:
            </p>
            <CodeBlock code={sdkCode} />
          </div>
        </Card>

        {/* Supported models */}
        <Card title="Supported Models">
          <div className="flex flex-col gap-2">
            <p className="text-sm text-[#64748b] mb-2">
              TokenBudget supports automatic pricing for these model families:
            </p>
            {[
              { name: 'OpenAI', models: 'gpt-4o, gpt-4o-mini, gpt-4, gpt-3.5-turbo, o1, o3' },
              { name: 'Anthropic', models: 'claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3-5-sonnet, claude-opus-4' },
              { name: 'Google', models: 'gemini-1.5-pro, gemini-1.5-flash, gemini-pro' },
            ].map(({ name, models }) => (
              <div key={name} className="flex gap-3 py-2.5 border-b border-[#1e1e2e] last:border-0">
                <span className="text-sm font-medium text-[#e2e8f0] w-24 flex-shrink-0">{name}</span>
                <span className="text-sm text-[#64748b]">{models}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
