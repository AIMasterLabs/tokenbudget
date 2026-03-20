// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { Link } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { enableDemoMode } from '@/lib/demoData'
import {
  ArrowRight, ChevronDown, Zap, BarChart3, Bell, Rocket,
  Monitor, DollarSign, Bug, LayoutDashboard, Quote,
  TrendingUp, Activity, FileText, Shield, Users
} from 'lucide-react'

/* ═══════════════════════════════════════════════
   TokenBudget Landing Page
   Aesthetic: Editorial tech-noir — cinematic,
   sharp typography, documentary-style quotes
   ═══════════════════════════════════════════════ */

const PAIN_POINTS = [
  { icon: DollarSign, text: 'Your AI bill tripled last month and you have no idea why' },
  { icon: BarChart3, text: 'You have 5 AI features but no idea which ones are actually profitable' },
  { icon: Bug, text: 'A single bug caused thousands of unwanted API calls overnight' },
  { icon: LayoutDashboard, text: 'You use OpenAI AND Anthropic AND Gemini — tracked in 3 separate dashboards' },
]

const FEATURES = [
  {
    icon: Monitor,
    title: 'All Providers, One Dashboard',
    desc: 'OpenAI, Anthropic, Gemini, and any OpenAI-compatible API. Stop logging into 3 dashboards.',
  },
  {
    icon: BarChart3,
    title: 'Cost by Feature & User',
    desc: 'Tag calls with feature name, user ID, or environment. See exactly which parts of your product are expensive.',
  },
  {
    icon: Bell,
    title: 'Budget Alerts Before It\'s Too Late',
    desc: 'Set daily, weekly, or monthly limits. Get alerted at 50%, 80%, 100% — before you blow past your budget.',
  },
  {
    icon: Rocket,
    title: 'Ship in 5 Minutes',
    desc: 'Works with your existing client. No refactoring. No new infrastructure.',
  },
]

const QUOTES = [
  {
    text: 'It is now one of the recruiting tools in Silicon Valley: How many tokens comes along with my job? Every engineer that has access to tokens will be more productive.',
    author: 'Jensen Huang',
    role: 'CEO, NVIDIA',
    event: 'GTC 2026 Keynote — March 16, 2026',
    accent: '#76b900',
  },
  {
    text: 'Your data centre used to be a data centre for files. It\'s now a factory to generate tokens. Just as cloud computing introduced FinOps, AI factories are introducing token budgets.',
    author: 'Jensen Huang',
    role: 'CEO, NVIDIA',
    event: 'GTC 2026',
    accent: '#76b900',
  },
  {
    text: 'Our costs have more than tripled since November. Between the inference cost we pay AWS, between Cursor, between Anthropic — we are just spending millions.',
    author: 'Chamath Palihapitiya',
    role: 'Founder, Social Capital',
    event: 'All-In Podcast, 2026',
    accent: '#f59e0b',
  },
]


const HORROR_STATS = [
  {
    stat: 'A stolen API key cost one startup $82,314 in a single night',
    source: 'The Register, March 2026',
  },
  {
    stat: "Google's billing bug charged developers $70,000+ for services they never used",
    source: 'Google AI Studio, August 2025',
  },
  {
    stat: 'Chamath: "Our AI inference costs have more than tripled since November… we are just spending millions"',
    source: 'All-In Podcast, 2026',
  },
]

const PLATFORM_STATS_SIMPLE = [
  { value: '2 min', label: 'Average setup time' },
  { value: 'Free', label: 'Open source' },
  { value: '3', label: 'AI providers supported' },
  { value: '1 line', label: 'Code change required' },
]

const DASHBOARD_MODELS = [
  { name: 'gpt-4o', cost: 4827.32, pct: 42, color: '#6366f1', requests: 142_300 },
  { name: 'claude-sonnet', cost: 2941.18, pct: 26, color: '#818cf8', requests: 89_400 },
  { name: 'gpt-4o-mini', cost: 1823.45, pct: 16, color: '#a78bfa', requests: 312_800 },
  { name: 'gpt-3.5-turbo', cost: 1072.91, pct: 9, color: '#c4b5fd', requests: 521_200 },
  { name: 'claude-haiku', cost: 743.14, pct: 7, color: '#ddd6fe', requests: 278_600 },
]

const LIVE_EVENTS = [
  { model: 'gpt-4o', cost: 0.0034, feature: 'chatbot', latency: 820 },
  { model: 'claude-sonnet', cost: 0.0128, feature: 'code-review', latency: 2140 },
  { model: 'gpt-4o-mini', cost: 0.0003, feature: 'autocomplete', latency: 340 },
  { model: 'gpt-4o', cost: 0.0089, feature: 'summarize', latency: 1450 },
  { model: 'claude-haiku', cost: 0.0002, feature: 'classify', latency: 190 },
  { model: 'gpt-3.5-turbo', cost: 0.0007, feature: 'embed', latency: 280 },
  { model: 'claude-sonnet', cost: 0.0156, feature: 'agent-loop', latency: 3200 },
  { model: 'gpt-4o', cost: 0.0045, feature: 'search', latency: 950 },
]

// ─── Counting animation hook ───
function useCountUp(target: number, duration = 2000, startOnView = true) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const started = useRef(false)

  useEffect(() => {
    if (!startOnView) {
      animateCount()
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true
          animateCount()
        }
      },
      { threshold: 0.3 }
    )
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()

    function animateCount() {
      const start = performance.now()
      const step = (now: number) => {
        const elapsed = now - start
        const progress = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
        setCount(Math.floor(eased * target))
        if (progress < 1) requestAnimationFrame(step)
      }
      requestAnimationFrame(step)
    }
  }, [target, duration, startOnView])

  return { count, ref }
}

function formatCompact(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K'
  return n.toLocaleString()
}

// ─── Reusable section wrapper ───
function Section({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={`relative px-6 md:px-8 ${className}`}>
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent-2)] mb-4">
      <span className="inline-block w-6 h-px bg-[var(--accent)]" />
      {children}
    </span>
  )
}

// ─── Hero ───
function Hero() {
  return (
    <Section className="pt-32 pb-24 md:pt-44 md:pb-32">
      {/* Background glow */}
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/4 w-[900px] h-[600px] rounded-full"
          style={{
            background: 'radial-gradient(ellipse at center, rgba(99,102,241,0.12) 0%, rgba(99,102,241,0.04) 40%, transparent 70%)',
          }}
        />
        {/* Grid overlay */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(var(--accent) 1px, transparent 1px), linear-gradient(90deg, var(--accent) 1px, transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
      </div>

      <div className="relative text-center">
        {/* Live ticker badge */}
        <LiveTickerBadge />

        {/* Headline */}
        <h1
          className="text-5xl md:text-7xl lg:text-[5.5rem] font-extrabold tracking-tight leading-[0.95] mb-6 animate-slide-up"
          style={{ animationDelay: '80ms', animationFillMode: 'both' }}
        >
          Stop Guessing
          <br />
          <span className="gradient-text">What Your AI Costs</span>
        </h1>

        {/* Subheadline */}
        <p
          className="mx-auto max-w-2xl text-lg md:text-xl leading-relaxed text-[var(--muted)] mb-10 animate-slide-up"
          style={{ animationDelay: '180ms', animationFillMode: 'both' }}
        >
          TokenBudget tracks every OpenAI, Anthropic, and Gemini API call across your
          entire product — so you know exactly which feature, which user, and which
          customer is burning your budget. Set limits before you get a surprise bill.
        </p>

        {/* CTAs */}
        <div
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6 animate-slide-up"
          style={{ animationDelay: '280ms', animationFillMode: 'both' }}
        >
          <Link
            to="/login"
            className="btn-primary text-base px-8 py-3.5 rounded-xl flex items-center gap-2 group"
          >
            Get Started
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <a
            href="#how-it-works"
            className="btn-ghost text-base flex items-center gap-1.5"
          >
            See how it works
            <ChevronDown className="w-4 h-4" />
          </a>
        </div>
      </div>
    </Section>
  )
}

// ─── Social Proof Banner ───
function SocialProofBanner() {
  return (
    <div className="relative border-y border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <div className="mx-auto max-w-6xl px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
        {HORROR_STATS.map((item, i) => (
          <div
            key={i}
            className="flex flex-col gap-2 animate-slide-up"
            style={{ animationDelay: `${i * 100}ms`, animationFillMode: 'both' }}
          >
            <p className="text-sm leading-relaxed text-[var(--text)] font-medium">
              "{item.stat}"
            </p>
            <span className="text-xs text-[var(--muted)]">— {item.source}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Problem Section ───
function ProblemSection() {
  return (
    <Section className="py-24 md:py-32">
      <div className="text-center mb-14">
        <SectionLabel>The Problem</SectionLabel>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
          Sound familiar?
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PAIN_POINTS.map((item, i) => (
          <div
            key={i}
            className="card-hover group flex items-start gap-4 cursor-default"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[var(--danger)]/10 flex items-center justify-center">
              <item.icon className="w-5 h-5 text-[var(--danger)]" />
            </div>
            <p className="text-[var(--text)] leading-relaxed pt-1.5">
              {item.text}
            </p>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ─── Quotes Section ───
function QuotesSection() {
  return (
    <Section className="py-24 md:py-32">
      <div className="text-center mb-14">
        <SectionLabel>Industry Signals</SectionLabel>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight max-w-3xl mx-auto">
          The world's most important technologists are talking about{' '}
          <span className="gradient-text">token budgets</span>
        </h2>
      </div>

      <div className="space-y-6">
        {QUOTES.map((q, i) => (
          <div
            key={i}
            className="card relative overflow-hidden group"
          >
            {/* Accent bar */}
            <div
              className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl"
              style={{ backgroundColor: q.accent }}
            />

            <div className="pl-6 flex flex-col md:flex-row md:items-start gap-4">
              <Quote
                className="flex-shrink-0 w-8 h-8 mt-1 opacity-20"
                style={{ color: q.accent }}
              />
              <div className="flex-1">
                <blockquote className="text-lg md:text-xl leading-relaxed text-[var(--text)] mb-4 font-medium italic">
                  "{q.text}"
                </blockquote>
                <div className="flex items-center gap-3">
                  {/* Avatar placeholder */}
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ backgroundColor: q.accent }}
                  >
                    {q.author.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">{q.author}</p>
                    <p className="text-xs text-[var(--muted)]">{q.role} · {q.event}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ─── Solution / Code Section ───
function SolutionSection() {
  return (
    <Section className="py-24 md:py-32" id="how-it-works">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* Left: Text */}
        <div>
          <SectionLabel>The Solution</SectionLabel>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
            One SDK.
            <br />
            Every provider.
            <br />
            <span className="gradient-text">Total visibility.</span>
          </h2>
          <p className="text-lg text-[var(--muted)] leading-relaxed">
            Wrap your existing AI client with one line of code. TokenBudget
            automatically tracks every token, every cost, every latency —
            tagged by feature, user, and environment.
          </p>
        </div>

        {/* Right: Code block */}
        <div className="relative">
          {/* Glow behind code */}
          <div
            className="absolute -inset-4 rounded-2xl opacity-30 blur-2xl pointer-events-none"
            style={{ background: 'radial-gradient(ellipse, rgba(99,102,241,0.2), transparent 70%)' }}
          />

          <div className="relative rounded-xl border border-[var(--border)] bg-[#0c0c14] overflow-hidden">
            {/* Title bar */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)]">
              <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
              <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
              <span className="w-3 h-3 rounded-full bg-[#28c840]" />
              <span className="ml-2 text-xs text-[var(--muted)] font-mono">app.py</span>
            </div>

            <pre className="p-5 text-sm leading-relaxed overflow-x-auto font-mono">
              <code>
                <span className="text-[var(--muted)]"># Before TokenBudget</span>{'\n'}
                <span className="text-[#c792ea]">client</span>
                <span className="text-[var(--text)]"> = </span>
                <span className="text-[#82aaff]">openai</span>
                <span className="text-[var(--text)]">.</span>
                <span className="text-[#ffcb6b]">Client</span>
                <span className="text-[var(--text)]">()</span>{'\n'}
                {'\n'}
                <span className="text-[var(--accent-2)]"># After TokenBudget (one line)</span>{'\n'}
                <span className="text-[#c792ea]">client</span>
                <span className="text-[var(--text)]"> = </span>
                <span className="text-[#82aaff]">tokenbudget</span>
                <span className="text-[var(--text)]">.</span>
                <span className="text-[#ffcb6b]">wrap</span>
                <span className="text-[var(--text)]">(</span>{'\n'}
                <span className="text-[var(--text)]">    openai.</span>
                <span className="text-[#ffcb6b]">Client</span>
                <span className="text-[var(--text)]">(),</span>{'\n'}
                <span className="text-[var(--text)]">    </span>
                <span className="text-[#f78c6c]">api_key</span>
                <span className="text-[var(--text)]">=</span>
                <span className="text-[#c3e88d]">"tb_ak_..."</span>{'\n'}
                <span className="text-[var(--text)]">)</span>{'\n'}
                {'\n'}
                <span className="text-[var(--muted)]"># Every call is now tracked automatically</span>{'\n'}
                <span className="text-[#c792ea]">response</span>
                <span className="text-[var(--text)]"> = client.chat.completions.</span>
                <span className="text-[#ffcb6b]">create</span>
                <span className="text-[var(--text)]">(</span>{'\n'}
                <span className="text-[var(--text)]">    </span>
                <span className="text-[#f78c6c]">model</span>
                <span className="text-[var(--text)]">=</span>
                <span className="text-[#c3e88d]">"gpt-4o"</span>
                <span className="text-[var(--text)]">,</span>{'\n'}
                <span className="text-[var(--text)]">    </span>
                <span className="text-[#f78c6c]">messages</span>
                <span className="text-[var(--text)]">=[{'{'}...</span>
                <span className="text-[var(--text)]">{'}'}]</span>{'\n'}
                <span className="text-[var(--text)]">)</span>{'\n'}
                <span className="text-emerald-400"># → $0.002, 850ms, feature="chatbot", user="u_123"</span>
              </code>
            </pre>
          </div>
        </div>
      </div>
    </Section>
  )
}

// ─── Features Section ───
function FeaturesSection() {
  return (
    <Section className="py-24 md:py-32">
      <div className="text-center mb-14">
        <SectionLabel>Features</SectionLabel>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
          Everything you need to control AI costs
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {FEATURES.map((f, i) => (
          <div key={i} className="card-hover group">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/10 flex items-center justify-center">
                <f.icon className="w-5 h-5 text-[var(--accent-2)]" />
              </div>
              <h3 className="text-lg font-semibold text-[var(--text)]">{f.title}</h3>
            </div>
            <p className="text-[var(--muted)] leading-relaxed pl-[52px]">{f.desc}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ─── Waitlist Section ───
function WaitlistSection() {
  return (
    <Section className="py-24 md:py-32" id="waitlist">
      <WaitlistForm />
    </Section>
  )
}

// ─── Waitlist Form ───
function WaitlistForm() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || !email.includes('@')) return
    setStatus('loading')
    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'landing-waitlist' }),
      })
      if (res.ok) setStatus('success')
      else setStatus('error')
    } catch {
      setStatus('error')
    }
  }

  if (status === 'success') {
    return (
      <div className="mt-12 text-center animate-fade-in">
        <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-5 py-2.5 text-sm text-emerald-400">
          <Zap className="w-4 h-4" />
          You're on the list! We'll be in touch.
        </div>
      </div>
    )
  }

  return (
    <div className="mt-12 text-center">
      <p className="text-sm text-[var(--muted)] mb-3">Get notified about new features.</p>
      <form onSubmit={handleSubmit} className="inline-flex gap-2 max-w-md w-full">
        <input
          type="email"
          className="input flex-1"
          placeholder="you@company.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <button type="submit" disabled={status === 'loading'} className="btn-primary px-5 whitespace-nowrap text-sm">
          {status === 'loading' ? 'Joining...' : 'Join Waitlist'}
        </button>
      </form>
      {status === 'error' && <p className="text-xs text-red-400 mt-2">Something went wrong. Try again.</p>}
    </div>
  )
}

// ─── PDF Report Preview ───
function ReportPreviewSection() {
  return (
    <Section className="py-24 md:py-32">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* Left text */}
        <div>
          <SectionLabel>Reports</SectionLabel>
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
            One-click reports for your
            <br />
            <span className="gradient-text">team and investors</span>
          </h2>
          <p className="text-lg text-[var(--muted)] leading-relaxed mb-8">
            Generate professional AI cost reports instantly. Share with your CFO,
            include in board decks, or attach to investor updates.
          </p>
          <button
            onClick={() => { enableDemoMode(); window.location.href = '/dashboard/analytics' }}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <FileText size={16} />
            Try Sample Report
          </button>
        </div>

        {/* Right: PDF mockup */}
        <div className="relative">
          <div className="absolute -inset-4 rounded-2xl opacity-20 blur-2xl pointer-events-none"
            style={{ background: 'radial-gradient(ellipse, rgba(99,102,241,0.15), transparent 70%)' }} />

          <div className="relative rounded-xl border border-[var(--border)] bg-white overflow-hidden shadow-2xl">
            {/* PDF header */}
            <div className="px-8 py-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded bg-indigo-600 flex items-center justify-center">
                    <Zap size={12} className="text-white" />
                  </div>
                  <span className="text-sm font-bold text-gray-900">TokenBudget</span>
                </div>
                <span className="text-xs text-gray-400">CONFIDENTIAL</span>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mt-3">AI Cost Report — March 2026</h3>
              <p className="text-xs text-gray-500 mt-1">Generated for Acme Corp · 30-day period</p>
            </div>

            {/* Executive Summary */}
            <div className="px-8 py-5">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">Executive Summary</h4>
              <ul className="space-y-1.5 text-xs text-gray-600">
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 mt-0.5">●</span>
                  Total AI spend: $11,408 (+12.3% MoM)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 mt-0.5">●</span>
                  Most expensive feature: Code Review ($4,827 — 42% of total)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-500 mt-0.5">●</span>
                  Budget utilization: 73% ($15,000 monthly limit)
                </li>
              </ul>
            </div>

            {/* Mini table */}
            <div className="px-8 pb-5">
              <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-3">Cost Breakdown</h4>
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500">
                    <th className="text-left py-1.5 font-medium">Model</th>
                    <th className="text-right py-1.5 font-medium">Requests</th>
                    <th className="text-right py-1.5 font-medium">Cost</th>
                    <th className="text-right py-1.5 font-medium">Share</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700">
                  {DASHBOARD_MODELS.slice(0, 4).map(m => (
                    <tr key={m.name} className="border-b border-gray-100">
                      <td className="py-1.5 font-medium">{m.name}</td>
                      <td className="text-right py-1.5 tabular-nums">{(m.requests / 1000).toFixed(1)}K</td>
                      <td className="text-right py-1.5 tabular-nums">${m.cost.toLocaleString()}</td>
                      <td className="text-right py-1.5">{m.pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mini chart bars */}
            <div className="px-8 pb-6">
              <div className="flex items-end gap-1.5 h-12">
                {[35, 45, 30, 55, 40, 60, 50, 65, 55, 70, 60, 75, 80, 72, 85].map((h, i) => (
                  <div key={i} className="flex-1 rounded-sm" style={{
                    height: `${h}%`,
                    backgroundColor: i >= 12 ? '#6366f1' : '#e0e7ff',
                  }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Section>
  )
}

// ─── Footer ───
function Footer() {
  return (
    <footer className="border-t border-[var(--border)] px-6 py-12 mt-12">
      <div className="mx-auto max-w-6xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <p className="text-sm font-semibold text-[var(--text)] mb-1">
            TokenBudget — The missing observability layer for AI-powered products.
          </p>
          <p className="text-xs text-[var(--muted)]">
            Built for developers who are tired of surprise AI bills.
          </p>
        </div>

        <div className="flex items-center gap-6 text-sm text-[var(--muted)]">
          <a href="#" className="hover:text-[var(--text)] transition-colors">Docs</a>
          <a href="https://github.com" className="hover:text-[var(--text)] transition-colors">GitHub</a>
          <a href="#" className="hover:text-[var(--text)] transition-colors">Status</a>
        </div>
      </div>
    </footer>
  )
}

// ─── Live Ticker Badge ───
function LiveTickerBadge() {
  const [tracked, setTracked] = useState(2_417_832)
  const [eventIdx, setEventIdx] = useState(0)
  useEffect(() => {
    const costTimer = setInterval(() => {
      setTracked(t => t + Math.floor(Math.random() * 265) + 47)
    }, 4000)
    const eventTimer = setInterval(() => setEventIdx(i => (i + 1) % LIVE_EVENTS.length), 2800)
    return () => { clearInterval(costTimer); clearInterval(eventTimer) }
  }, [])
  const ev = LIVE_EVENTS[eventIdx]
  const display = `$${(tracked / 1_000_000).toFixed(1)}M`
  return (
    <div className="flex flex-col items-center gap-3 mb-8 animate-fade-in">
      <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-1.5 text-xs text-[var(--muted)]">
        <span className="relative flex h-2 w-2 flex-shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
        <span className="tabular-nums">{display} in AI spend tracked</span>
      </div>
      <div className="inline-flex items-center gap-3 rounded-full border border-[var(--border)] bg-[var(--bg)] px-4 py-1.5 text-[10px] text-[var(--muted)] font-mono overflow-hidden">
        <span className="text-[var(--accent-2)]">{ev.model}</span>
        <span className="text-[var(--border)]">|</span>
        <span className="text-emerald-400">${ev.cost.toFixed(4)}</span>
        <span className="text-[var(--border)]">|</span>
        <span>{ev.feature}</span>
        <span className="text-[var(--border)]">|</span>
        <span>{ev.latency}ms</span>
      </div>
    </div>
  )
}

// ─── Platform Stats Bar ───
function PlatformStatsBar() {
  return (
    <Section className="py-16">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {PLATFORM_STATS_SIMPLE.map((stat, i) => (
          <div key={i} className="text-center">
            <div className="text-2xl md:text-3xl font-extrabold text-[var(--text)]">
              {stat.value}
            </div>
            <div className="text-xs uppercase tracking-wider text-[var(--muted)] mt-1">
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

// ─── Dashboard Preview ───
function DashboardPreview() {
  const { count: totalSpend, ref: spendRef } = useCountUp(11408, 2500)
  const { count: totalReqs, ref: reqsRef } = useCountUp(1344300, 2500)

  return (
    <Section className="py-24 md:py-32" id="dashboard-preview">
      <div className="text-center mb-14">
        <SectionLabel>Live Dashboard</SectionLabel>
        <h2 className="text-3xl md:text-5xl font-bold tracking-tight">
          See everything. <span className="gradient-text">Miss nothing.</span>
        </h2>
      </div>

      {/* Fake dashboard window */}
      <div className="relative">
        <div className="absolute -inset-6 rounded-3xl opacity-20 blur-3xl pointer-events-none"
          style={{ background: 'radial-gradient(ellipse, rgba(99,102,241,0.15), transparent 70%)' }} />

        <div className="relative rounded-2xl border border-[var(--border)] bg-[#0c0c14] overflow-hidden shadow-2xl">
          {/* Window chrome */}
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-[var(--border)] bg-[var(--surface)]">
            <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
            <span className="w-3 h-3 rounded-full bg-[#28c840]" />
            <span className="ml-3 text-xs text-[var(--muted)] font-mono">dashboard.tokenbudget.com</span>
          </div>

          <div className="p-6 md:p-8">
            {/* Hero stats row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Total Spend', value: `$${totalSpend.toLocaleString()}`, trend: '+12.3%', up: true, ref: spendRef },
                { label: 'API Requests', value: formatCompact(totalReqs), trend: '+8.7%', up: true, ref: reqsRef },
                { label: 'Avg Cost/Req', value: '$0.0085', trend: '-4.2%', up: false },
                { label: 'Budget Used', value: '73%', trend: '27% remaining', up: false },
              ].map((s, i) => (
                <div key={i} ref={s.ref} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
                  <div className="text-xs text-[var(--muted)] mb-1">{s.label}</div>
                  <div className="text-xl md:text-2xl font-bold text-[var(--text)] tabular-nums">{s.value}</div>
                  <div className={`text-xs mt-1 flex items-center gap-1 ${s.up ? 'text-emerald-400' : 'text-amber-400'}`}>
                    <TrendingUp className={`w-3 h-3 ${!s.up ? 'rotate-180' : ''}`} />
                    {s.trend}
                  </div>
                </div>
              ))}
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Spend chart (fake SVG area) */}
              <div className="md:col-span-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="text-sm font-semibold text-[var(--text)] mb-4">Spend Over Time</div>
                <svg viewBox="0 0 600 160" className="w-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0,120 C50,110 80,95 120,100 C160,105 200,60 250,70 C300,80 340,40 380,35 C420,30 460,50 500,25 C540,15 570,20 600,10 L600,160 L0,160 Z"
                    fill="url(#spendGrad)" />
                  <path d="M0,120 C50,110 80,95 120,100 C160,105 200,60 250,70 C300,80 340,40 380,35 C420,30 460,50 500,25 C540,15 570,20 600,10"
                    fill="none" stroke="#6366f1" strokeWidth="2.5" />
                  {/* Animated dot at the end */}
                  <circle cx="600" cy="10" r="4" fill="#6366f1">
                    <animate attributeName="r" values="4;6;4" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite" />
                  </circle>
                </svg>
                <div className="flex justify-between text-[10px] text-[var(--muted)] mt-2 px-1">
                  {['Mar 1','Mar 5','Mar 9','Mar 13','Mar 17'].map(d => <span key={d}>{d}</span>)}
                </div>
              </div>

              {/* Model breakdown */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="text-sm font-semibold text-[var(--text)] mb-4">By Model</div>
                <div className="space-y-3">
                  {DASHBOARD_MODELS.map((m) => (
                    <div key={m.name}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--text)] font-medium">{m.name}</span>
                        <span className="text-[var(--muted)] tabular-nums">${m.cost.toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-1000 ease-out"
                          style={{
                            width: `${m.pct}%`,
                            backgroundColor: m.color,
                            animation: 'slideRight 1.5s ease-out forwards',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Second row: Feature costs + User breakdown + Budget */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              {/* Per-feature cost */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text)] mb-4">
                  <BarChart3 className="w-4 h-4 text-[var(--accent-2)]" />
                  Cost by Feature
                </div>
                <div className="space-y-3">
                  {[
                    { name: 'chatbot', cost: 3420, pct: 30, color: '#6366f1' },
                    { name: 'code-review', cost: 2890, pct: 25, color: '#818cf8' },
                    { name: 'summarize', cost: 2100, pct: 18, color: '#a78bfa' },
                    { name: 'autocomplete', cost: 1650, pct: 14, color: '#c4b5fd' },
                    { name: 'agent-loop', cost: 1348, pct: 12, color: '#ddd6fe' },
                  ].map(f => (
                    <div key={f.name}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--text)] font-medium">{f.name}</span>
                        <span className="text-[var(--muted)] tabular-nums">${f.cost.toLocaleString()}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${f.pct}%`, backgroundColor: f.color }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Per-user breakdown */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text)] mb-4">
                  <Users className="w-4 h-4 text-[var(--accent-2)]" />
                  Cost by User
                </div>
                <div className="space-y-2.5">
                  {[
                    { id: 'user-alice', cost: 4210, reqs: '412K' },
                    { id: 'user-bob', cost: 3180, reqs: '389K' },
                    { id: 'user-carol', cost: 2450, reqs: '298K' },
                    { id: 'user-dave', cost: 1568, reqs: '245K' },
                  ].map(u => (
                    <div key={u.id} className="flex items-center justify-between py-1.5 border-b border-[var(--border)] last:border-0">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-[8px] font-bold text-[var(--accent-2)]">
                          {u.id.split('-')[1][0].toUpperCase()}
                        </div>
                        <span className="text-xs text-[var(--text)]">{u.id}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-medium text-[var(--text)] tabular-nums">${u.cost.toLocaleString()}</div>
                        <div className="text-[10px] text-[var(--muted)]">{u.reqs} reqs</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Budget gauges + alerts */}
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text)] mb-4">
                  <Shield className="w-4 h-4 text-[var(--accent-2)]" />
                  Budgets & Alerts
                </div>
                {/* Budget bars */}
                <div className="space-y-3 mb-5">
                  {[
                    { name: 'Monthly Prod', used: 73, limit: '$15,000', color: '#6366f1' },
                    { name: 'Daily Safety', used: 45, limit: '$500', color: '#818cf8' },
                  ].map(b => (
                    <div key={b.name}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[var(--text)]">{b.name}</span>
                        <span className="text-[var(--muted)]">{b.used}% of {b.limit}</span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--surface-2)] overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${b.used}%`, backgroundColor: b.used > 80 ? '#f59e0b' : b.color }} />
                      </div>
                    </div>
                  ))}
                </div>
                {/* Recent alerts */}
                <div className="text-xs font-medium text-[var(--text)] mb-2">Recent Alerts</div>
                <div className="space-y-1.5">
                  {[
                    { msg: 'Monthly budget at 80%', time: '2h ago', type: 'warn' },
                    { msg: 'Spike: 3x normal in "chatbot"', time: '5h ago', type: 'danger' },
                    { msg: 'New model detected: o4-mini', time: '1d ago', type: 'info' },
                  ].map((a, i) => (
                    <div key={i} className="flex items-center gap-2 py-1 px-2 rounded bg-[var(--bg)] text-[var(--muted)]">
                      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${a.type === 'danger' ? 'bg-red-400' : a.type === 'warn' ? 'bg-amber-400' : 'bg-blue-400'}`} />
                      <span className="text-[10px] flex-1">{a.msg}</span>
                      <span className="text-[10px] text-[var(--muted)]">{a.time}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Live event feed */}
            <div className="mt-6 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
              <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text)] mb-3">
                <Activity className="w-4 h-4 text-emerald-400" />
                Live Event Feed
              </div>
              <div className="space-y-1.5 font-mono text-xs">
                {LIVE_EVENTS.slice(0, 5).map((ev, i) => (
                  <div key={i} className="flex items-center gap-4 py-1 px-2 rounded bg-[var(--bg)] text-[var(--muted)]"
                    style={{ animation: `fadeIn 0.3s ease ${i * 100}ms both` }}>
                    <span className="text-[var(--accent-2)] w-28">{ev.model}</span>
                    <span className="text-emerald-400 w-16">${ev.cost.toFixed(4)}</span>
                    <span className="w-24">{ev.feature}</span>
                    <span className="w-14 text-right">{ev.latency}ms</span>
                    <span className="text-[var(--border)]">·</span>
                    <span className="text-[var(--muted-2)]">just now</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA below preview */}
      <div className="text-center mt-10">
        <button
          onClick={() => { enableDemoMode(); window.location.href = '/dashboard' }}
          className="btn-primary text-base px-8 py-3.5 rounded-xl inline-flex items-center gap-2 group"
        >
          Try the live demo
          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    </Section>
  )
}

// ─── Nav bar ───
function NavBar() {
  return (
    <nav className="fixed top-0 inset-x-0 z-50 border-b border-[var(--border)]"
      style={{ background: 'rgba(10,10,15,0.8)', backdropFilter: 'blur(12px)' }}
    >
      <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #818cf8)' }}
          >
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-bold text-[var(--text)]">TokenBudget</span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-6 text-sm text-[var(--muted)]">
          <a href="#how-it-works" className="hover:text-[var(--text)] transition-colors">How it works</a>
          <Link to="/login" className="hover:text-[var(--text)] transition-colors">Login</Link>
          <Link to="/login" className="btn-primary text-sm px-4 py-2 rounded-lg">
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  )
}

// ─── Page ───
export function Landing() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <NavBar />
      <Hero />
      <PlatformStatsBar />
      <SocialProofBanner />
      <ProblemSection />
      <QuotesSection />
      <SolutionSection />
      <DashboardPreview />
      <FeaturesSection />
      <ReportPreviewSection />
      <WaitlistSection />
      <Footer />
    </div>
  )
}
