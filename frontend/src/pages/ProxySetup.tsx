// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { CheckCircle, Copy, Check } from 'lucide-react'
import { clsx } from 'clsx'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiKey(): string {
  return localStorage.getItem('tb_api_key') || 'YOUR_TB_KEY'
}

const PROXY_BASE = window.location.origin

// ---------------------------------------------------------------------------
// Code examples
// ---------------------------------------------------------------------------

function openaiPythonCode(tbKey: string): string {
  return `import openai

client = openai.OpenAI(
    api_key="YOUR_OPENAI_API_KEY",   # your real OpenAI key
    base_url="${PROXY_BASE}/proxy/openai/v1",
    default_headers={
        "X-TokenBudget-Key": "${tbKey}",
        # Optional metadata
        # "X-TB-Feature": "chat",
        # "X-TB-User":    "user_123",
        # "X-TB-Project": "my-app",
    },
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.choices[0].message.content)
# TokenBudget automatically records tokens + cost — no code changes needed.
`
}

function anthropicPythonCode(tbKey: string): string {
  return `import anthropic

client = anthropic.Anthropic(
    api_key="YOUR_ANTHROPIC_API_KEY",   # your real Anthropic key
    base_url="${PROXY_BASE}/proxy/anthropic",
    default_headers={
        "X-TokenBudget-Key": "${tbKey}",
        # Optional metadata
        # "X-TB-Feature": "summarise",
        # "X-TB-User":    "user_456",
    },
)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude!"}],
)

print(message.content[0].text)
# TokenBudget silently records usage in the background.
`
}

function nodejsCode(tbKey: string): string {
  return `import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_OPENAI_API_KEY",   // your real OpenAI key
  baseURL: "${PROXY_BASE}/proxy/openai/v1",
  defaultHeaders: {
    "X-TokenBudget-Key": "${tbKey}",
    // Optional metadata
    // "X-TB-Feature": "node-chat",
    // "X-TB-User":    "user_789",
  },
});

const completion = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello from Node.js!" }],
});

console.log(completion.choices[0].message.content);
// Token usage is automatically tracked by TokenBudget.
`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(code.trim()).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="relative group">
      <pre
        className="bg-[#07070d] border border-[#1e1e2e] rounded-lg p-4 overflow-x-auto text-xs text-[#e2e8f0] leading-relaxed"
        style={{ fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace" }}
      >
        <code className={`language-${language}`}>{code.trim()}</code>
      </pre>
      <button
        onClick={handleCopy}
        className={clsx(
          'absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium',
          'transition-all duration-150',
          copied
            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            : 'bg-[#1e1e2e] text-[#64748b] border border-[#2a2a3d] hover:text-[#c4c4e0] hover:border-[#6366f1]/40'
        )}
      >
        {copied ? <Check size={12} /> : <Copy size={12} />}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}

type Tab = 'openai' | 'anthropic' | 'nodejs'

interface TabItem {
  id: Tab
  label: string
  badge?: string
}

const TABS: TabItem[] = [
  { id: 'openai',    label: 'OpenAI Python' },
  { id: 'anthropic', label: 'Anthropic Python' },
  { id: 'nodejs',    label: 'Node.js' },
]

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function ProxySetup() {
  const [activeTab, setActiveTab] = useState<Tab>('openai')
  const tbKey = getApiKey()

  const codeMap: Record<Tab, string> = {
    openai:    openaiPythonCode(tbKey),
    anthropic: anthropicPythonCode(tbKey),
    nodejs:    nodejsCode(tbKey),
  }

  const langMap: Record<Tab, string> = {
    openai:    'python',
    anthropic: 'python',
    nodejs:    'typescript',
  }

  return (
    <div className="flex flex-col min-h-full">
      <Header title="Proxy Setup" />

      <div className="p-6 flex flex-col gap-6 max-w-3xl">

        {/* Security badge */}
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-xl"
          style={{
            background: 'linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.04) 100%)',
            border: '1px solid rgba(16,185,129,0.2)',
          }}
        >
          <CheckCircle size={18} className="text-emerald-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-300">
              Your API key is never stored by TokenBudget
            </p>
            <p className="text-xs text-emerald-600 mt-0.5">
              We proxy your requests transparently — only token counts and costs are recorded.
            </p>
          </div>
        </div>

        {/* How it works */}
        <Card title="How the Proxy Works">
          <ol className="flex flex-col gap-3 text-sm text-[#94a3b8]">
            {[
              'Point your AI client\'s base URL at TokenBudget\'s proxy.',
              'Add your TokenBudget key as the X-TokenBudget-Key header.',
              'TokenBudget forwards every request to OpenAI / Anthropic unchanged.',
              'The response is returned to you without any delay.',
              'Token usage and cost are recorded silently as a background task.',
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-3">
                <span
                  className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-[#818cf8]"
                  style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.2)' }}
                >
                  {i + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </Card>

        {/* Code examples */}
        <Card title="Integration Examples">
          {/* Tab bar */}
          <div
            className="flex gap-1 mb-5 p-1 rounded-lg"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid #1e1e2e' }}
          >
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={clsx(
                  'flex-1 px-3 py-2 rounded-md text-xs font-medium transition-all duration-150',
                  activeTab === id
                    ? 'text-[#c7d2fe] bg-[#6366f1]/15'
                    : 'text-[#64748b] hover:text-[#94a3b8]'
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Code */}
          <CodeBlock code={codeMap[activeTab]} language={langMap[activeTab]} />

          {/* Key hint */}
          <p className="text-xs text-[#64748b] mt-3">
            Your TokenBudget key{' '}
            <code className="text-[#818cf8] bg-[#1e1e2e] px-1.5 py-0.5 rounded font-mono text-[11px]">
              {tbKey.length > 20 ? `${tbKey.slice(0, 12)}…` : tbKey}
            </code>{' '}
            is pre-filled above. Rotate it any time on the{' '}
            <a href="/dashboard/keys" className="text-[#818cf8] underline underline-offset-2 hover:text-[#c7d2fe]">
              API Keys
            </a>{' '}
            page.
          </p>
        </Card>

        {/* Proxy endpoints reference */}
        <Card title="Proxy Endpoints">
          <div className="flex flex-col gap-2">
            {[
              { method: 'POST', path: '/proxy/openai/v1/chat/completions',  desc: 'OpenAI Chat Completions' },
              { method: 'POST', path: '/proxy/openai/v1/completions',        desc: 'OpenAI Completions (legacy)' },
              { method: 'POST', path: '/proxy/openai/v1/embeddings',         desc: 'OpenAI Embeddings' },
              { method: 'POST', path: '/proxy/anthropic/v1/messages',        desc: 'Anthropic Messages' },
            ].map(({ method, path, desc }) => (
              <div
                key={path}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #1e1e2e' }}
              >
                <span
                  className="flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded"
                  style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}
                >
                  {method}
                </span>
                <code className="text-xs text-[#c4c4e0] font-mono flex-1">{path}</code>
                <span className="text-xs text-[#475569] hidden sm:block">{desc}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-[#475569] mt-4">
            All endpoints accept the same request body as the original API — no schema changes required.
          </p>
        </Card>

        {/* Optional headers */}
        <Card title="Optional Metadata Headers">
          <div className="flex flex-col gap-2">
            {[
              { header: 'X-TB-Feature', desc: 'Tag requests by feature (e.g. "summarise", "chat")' },
              { header: 'X-TB-User',    desc: 'Associate usage with a user ID' },
              { header: 'X-TB-Project', desc: 'Override project for this request' },
              { header: 'X-TB-Tags',    desc: 'JSON object of arbitrary key/value tags' },
            ].map(({ header, desc }) => (
              <div key={header} className="flex items-start gap-3 text-sm">
                <code
                  className="flex-shrink-0 text-xs text-[#818cf8] bg-[#1e1e2e] px-2 py-0.5 rounded font-mono mt-0.5"
                >
                  {header}
                </code>
                <span className="text-[#64748b] text-xs leading-relaxed">{desc}</span>
              </div>
            ))}
          </div>
        </Card>

      </div>
    </div>
  )
}
