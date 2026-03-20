// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { AnalyticsSummary, ModelBreakdown, TimeseriesPoint, UserBreakdown, Granularity, Period, UsageSummary } from './types'

export async function getSummary(period: Period): Promise<AnalyticsSummary> {
  const { data } = await apiClient.get('/api/analytics/summary', { params: { period } })
  return data
}

export async function getByModel(period: Period): Promise<ModelBreakdown[]> {
  const { data } = await apiClient.get('/api/analytics/by-model', { params: { period } })
  return data
}

export async function getTimeseries(period: Period, granularity: Granularity = 'daily'): Promise<TimeseriesPoint[]> {
  const { data } = await apiClient.get('/api/analytics/timeseries', { params: { period, granularity } })
  return data
}

export async function getByUser(period: Period): Promise<UserBreakdown[]> {
  const { data } = await apiClient.get('/api/analytics/by-user', { params: { period } })
  return data
}

export async function getUsageSummary(): Promise<UsageSummary> {
  const { data } = await apiClient.get('/api/analytics/usage-summary')
  return data
}

export async function exportCSV(period: Period): Promise<Blob> {
  const { data } = await apiClient.get('/api/exports/csv', {
    params: { period },
    responseType: 'blob',
  })
  return data
}

export async function exportPDF(period: Period): Promise<Blob> {
  const { data } = await apiClient.get('/api/exports/pdf', {
    params: { period },
    responseType: 'blob',
  })
  return data
}
