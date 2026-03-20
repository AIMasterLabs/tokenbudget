// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

export interface AnalyticsSummary {
  total_cost_usd: number
  total_requests: number
  total_input_tokens: number
  total_output_tokens: number
  avg_cost_per_request: number
  avg_latency_ms: number
}

export interface ModelBreakdown {
  model: string
  total_cost_usd: number
  request_count: number
  percentage: number
}

export interface UserBreakdown {
  user_id: string
  total_cost_usd: number
  request_count: number
  percentage: number
}

export interface TimeseriesPoint {
  timestamp: string
  cost_usd: number
  request_count: number
}

export interface Budget {
  id: string
  name?: string
  amount_usd: number
  period: string
  alert_thresholds: number[]
  is_active: boolean
  current_spend_usd: number
  utilization_pct: number
  created_at: string
}

export interface BudgetCreatePayload {
  name?: string
  amount_usd: number
  period: string
  alert_thresholds: number[]
}

export interface ApiKeyResponse {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  created_at: string
}

export interface ApiKeyCreateResponse extends ApiKeyResponse {
  raw_key: string
}

export interface UsageSummary {
  tier: string
  events_this_month: number
  events_limit: number
  events_pct: number
  active_keys: number
  keys_limit: number
  keys_pct: number
  retention_days: number
  projects_limit: number
}

export type Period = '7d' | '30d' | '90d'
export type Granularity = 'hourly' | 'daily' | 'weekly'

// ── Alerts ──────────────────────────────────────────────────────────────────
export type AlertChannel = 'slack' | 'webhook'

export interface AlertConfig {
  id: string
  channel: AlertChannel
  url: string
  budget_id: string
  thresholds: number[]
  is_active: boolean
  created_at: string
}

export interface AlertConfigCreate {
  channel: AlertChannel
  url: string
  budget_id: string
  thresholds: number[]
}

// ── Auth ────────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
  role?: string
  department?: string
}

export interface UserInfo {
  id: string
  email: string
  name: string
  role: string
  department?: string
  is_active?: boolean
  created_at?: string
  groups?: string[]
}

export interface AuthResponse {
  token: string
  user: UserInfo
}

export interface ProjectMember {
  user_id: string
  user_email: string
  user_name: string
  role: string
  added_at: string
}

// ── Groups ─────────────────────────────────────────────────────────────────
export type Permission =
  | 'view_analytics'
  | 'view_costs'
  | 'view_users'
  | 'export_reports'
  | 'manage_keys'

export interface Group {
  id: string
  name: string
  description: string
  member_count: number
  project_count: number
  created_at: string
}

export interface GroupMember {
  user_id: string
  email: string
  name: string
  role: string
  added_at: string
}

export interface GroupProjectAccess {
  project_id: string
  project_name: string
  permissions: Permission[]
  added_at: string
}

export interface GroupDetail extends Group {
  members: GroupMember[]
  projects: GroupProjectAccess[]
}

// ── Bulk Users ─────────────────────────────────────────────────────────────
export interface BulkUserCreate {
  email: string
  password: string
  name: string
  role: string
  groups: string[]
}

export interface BulkUserResultEntry {
  email: string
  success: boolean
  error?: string
}

export interface BulkUserResult {
  created: number
  failed: number
  results: BulkUserResultEntry[]
}
