// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

export function formatCurrency(value: number): string {
  if (isNaN(value) || value == null) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value)
}

export function formatNumber(value: number): string {
  if (isNaN(value) || value == null) return '0'
  return new Intl.NumberFormat('en-US').format(Math.round(value))
}

export function formatTokens(value: number): string {
  if (isNaN(value) || value == null) return '0'
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }
  return formatNumber(value)
}

export function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatLatency(ms: number): string {
  if (isNaN(ms) || ms == null) return '0ms'
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`
  }
  return `${Math.round(ms)}ms`
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}
