// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

export const MODEL_COLORS: Record<string, string> = {
  'gpt-4': '#10b981',
  'gpt-4o': '#6366f1',
  'gpt-4o-mini': '#818cf8',
  'gpt-4-turbo': '#06b6d4',
  'gpt-3.5-turbo': '#f59e0b',
  'claude-3-opus-20240229': '#ec4899',
  'claude-3-sonnet-20240229': '#8b5cf6',
  'claude-3-haiku-20240307': '#14b8a6',
  'claude-3-5-sonnet-20241022': '#a78bfa',
  'claude-opus-4': '#f43f5e',
  'gemini-pro': '#22c55e',
  'gemini-1.5-pro': '#3b82f6',
  'gemini-1.5-flash': '#84cc16',
}

export const DEFAULT_COLORS = [
  '#6366f1',
  '#10b981',
  '#f59e0b',
  '#ec4899',
  '#06b6d4',
  '#8b5cf6',
  '#14b8a6',
  '#f43f5e',
  '#22c55e',
  '#3b82f6',
]

export function getModelColor(model: string, index = 0): string {
  return MODEL_COLORS[model] ?? DEFAULT_COLORS[index % DEFAULT_COLORS.length]
}

export const PERIOD_OPTIONS = [
  { label: '7 days', value: '7d' },
  { label: '30 days', value: '30d' },
  { label: '90 days', value: '90d' },
] as const

