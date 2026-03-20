// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

// ═══════════════════════════════════════
// Demo data for TokenBudget demo mode
// Stored in localStorage: tokenbudget_demo=true
// ═══════════════════════════════════════

export function isDemoMode(): boolean {
  return localStorage.getItem('tokenbudget_demo') === 'true'
}

export function enableDemoMode() {
  localStorage.setItem('tokenbudget_demo', 'true')
  localStorage.setItem('tb_api_key', 'tb_ak_demo_000000000000')
}

export function disableDemoMode() {
  localStorage.removeItem('tokenbudget_demo')
  localStorage.removeItem('tb_api_key')
}

// ─── Projects ───
export const DEMO_PROJECTS = [
  { id: 'p1', name: 'Mobile App', slug: 'mobile-app', description: 'iOS and Android app', color: '#3b82f6', is_active: true, created_at: '2026-02-15T00:00:00Z', spend: 4080, keys: 3, topModel: 'gpt-4o' },
  { id: 'p2', name: 'Web Dashboard', slug: 'web-dashboard', description: 'Main web application', color: '#8b5cf6', is_active: true, created_at: '2026-02-20T00:00:00Z', spend: 935, keys: 2, topModel: 'claude-sonnet' },
  { id: 'p3', name: 'Internal Tools', slug: 'internal-tools', description: 'Admin and ops tools', color: '#10b981', is_active: true, created_at: '2026-03-01T00:00:00Z', spend: 210, keys: 1, topModel: 'gpt-4o-mini' },
  { id: 'p4', name: 'Staging', slug: 'staging', description: 'Test environment', color: '#f59e0b', is_active: true, created_at: '2026-03-05T00:00:00Z', spend: 89, keys: 2, topModel: 'gpt-3.5-turbo' },
]

// ─── Analytics Summary ───
export const DEMO_SUMMARY = {
  total_cost_usd: 11408.0,
  total_requests: 1344300,
  total_input_tokens: 892_400_000,
  total_output_tokens: 214_800_000,
  avg_cost_per_request: 0.0085,
  avg_latency_ms: 1240,
}

// ─── Model Breakdown ───
export const DEMO_MODELS = [
  { model: 'gpt-4o', total_cost_usd: 4827.32, request_count: 142300, percentage: 42.3 },
  { model: 'claude-sonnet-4-20250514', total_cost_usd: 2941.18, request_count: 89400, percentage: 25.8 },
  { model: 'gpt-4o-mini', total_cost_usd: 1823.45, request_count: 312800, percentage: 16.0 },
  { model: 'gpt-3.5-turbo', total_cost_usd: 1072.91, request_count: 521200, percentage: 9.4 },
  { model: 'claude-haiku-4-5-20251001', total_cost_usd: 743.14, request_count: 278600, percentage: 6.5 },
]

// ─── 30 days of timeseries ───
function generateTimeseries(): Array<{ timestamp: string; cost_usd: number; request_count: number }> {
  const data = []
  const base = new Date('2026-02-18')
  const costs = [
    280, 310, 295, 340, 365, 120, 95,
    370, 390, 410, 380, 420, 150, 110,
    430, 460, 445, 490, 510, 180, 130,
    520, 540, 530, 570, 590, 200, 160,
    610, 640,
  ]
  for (let i = 0; i < 30; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i)
    data.push({
      timestamp: d.toISOString(),
      cost_usd: costs[i],
      request_count: Math.floor(costs[i] * 120 + Math.random() * 5000),
    })
  }
  return data
}
export const DEMO_TIMESERIES = generateTimeseries()

// ─── Budgets ───
export const DEMO_BUDGETS = [
  {
    id: 'b1', name: 'Monthly Production', amount_usd: 15000, period: 'monthly', alert_thresholds: [0.5, 0.8, 1.0],
    is_active: true, current_spend_usd: 10948, utilization_pct: 73, created_at: '2026-02-01T00:00:00Z',
  },
  {
    id: 'b2', name: 'Daily Safety Net', amount_usd: 500, period: 'daily', alert_thresholds: [0.8, 1.0],
    is_active: true, current_spend_usd: 225, utilization_pct: 45, created_at: '2026-03-01T00:00:00Z',
  },
]

// ─── API Keys ───
export const DEMO_KEYS = [
  { id: 'k1', name: 'production-main', key_prefix: 'tb_ak_9f2b', is_active: true, created_at: '2026-02-15T00:00:00Z', project: 'Mobile App' },
  { id: 'k2', name: 'production-chatbot', key_prefix: 'tb_ak_4c71', is_active: true, created_at: '2026-02-15T00:00:00Z', project: 'Mobile App' },
  { id: 'k3', name: 'web-frontend', key_prefix: 'tb_ak_a3e8', is_active: true, created_at: '2026-02-20T00:00:00Z', project: 'Web Dashboard' },
  { id: 'k4', name: 'internal-ops', key_prefix: 'tb_ak_d1f0', is_active: true, created_at: '2026-03-01T00:00:00Z', project: 'Internal Tools' },
  { id: 'k5', name: 'staging-test', key_prefix: 'tb_ak_7b22', is_active: true, created_at: '2026-03-05T00:00:00Z', project: 'Staging' },
  { id: 'k6', name: 'staging-ci', key_prefix: 'tb_ak_e5c9', is_active: false, created_at: '2026-03-05T00:00:00Z', project: 'Staging' },
]

// ─── Recent Events ───
export const DEMO_EVENTS = [
  { model: 'gpt-4o', cost_usd: 0.0034, feature: 'chatbot', latency_ms: 820, created_at: '2026-03-19T10:42:00Z' },
  { model: 'claude-sonnet-4-20250514', cost_usd: 0.0128, feature: 'code-review', latency_ms: 2140, created_at: '2026-03-19T10:41:30Z' },
  { model: 'gpt-4o-mini', cost_usd: 0.0003, feature: 'autocomplete', latency_ms: 340, created_at: '2026-03-19T10:41:00Z' },
  { model: 'gpt-4o', cost_usd: 0.0089, feature: 'summarize', latency_ms: 1450, created_at: '2026-03-19T10:40:30Z' },
  { model: 'claude-haiku-4-5-20251001', cost_usd: 0.0002, feature: 'classify', latency_ms: 190, created_at: '2026-03-19T10:40:00Z' },
  { model: 'gpt-3.5-turbo', cost_usd: 0.0007, feature: 'embed', latency_ms: 280, created_at: '2026-03-19T10:39:30Z' },
  { model: 'claude-sonnet-4-20250514', cost_usd: 0.0156, feature: 'agent-loop', latency_ms: 3200, created_at: '2026-03-19T10:39:00Z' },
  { model: 'gpt-4o', cost_usd: 0.0045, feature: 'search', latency_ms: 950, created_at: '2026-03-19T10:38:30Z' },
  { model: 'gpt-4o-mini', cost_usd: 0.0004, feature: 'autocomplete', latency_ms: 310, created_at: '2026-03-19T10:38:00Z' },
  { model: 'gpt-4o', cost_usd: 0.0067, feature: 'chatbot', latency_ms: 1120, created_at: '2026-03-19T10:37:30Z' },
]

// ─── User breakdown ───
export const DEMO_USERS = [
  { user_id: 'u1', total_cost_usd: 4210, request_count: 412000, percentage: 36.9 },
  { user_id: 'u2', total_cost_usd: 3180, request_count: 389000, percentage: 27.9 },
  { user_id: 'u3', total_cost_usd: 2450, request_count: 298000, percentage: 21.5 },
  { user_id: 'u4', total_cost_usd: 1568, request_count: 245300, percentage: 13.7 },
]
