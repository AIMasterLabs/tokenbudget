// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useQuery } from '@tanstack/react-query'
import { getSummary, getByModel, getTimeseries, getByUser, getUsageSummary } from '@/api/analytics'
import { isDemoMode, DEMO_SUMMARY, DEMO_MODELS, DEMO_TIMESERIES, DEMO_USERS } from '@/lib/demoData'
import type { Granularity, Period, AnalyticsSummary, ModelBreakdown, TimeseriesPoint, UserBreakdown, UsageSummary } from '@/api/types'

export function useSummary(period: Period = '30d') {
  return useQuery<AnalyticsSummary>({
    queryKey: ['analytics', 'summary', period],
    queryFn: () => isDemoMode() ? Promise.resolve(DEMO_SUMMARY) : getSummary(period),
    staleTime: 60_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useByModel(period: Period = '30d') {
  return useQuery<ModelBreakdown[]>({
    queryKey: ['analytics', 'by-model', period],
    queryFn: () => isDemoMode() ? Promise.resolve(DEMO_MODELS) : getByModel(period),
    staleTime: 60_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useTimeseries(period: Period = '30d', granularity: Granularity = 'daily') {
  return useQuery<TimeseriesPoint[]>({
    queryKey: ['analytics', 'timeseries', period, granularity],
    queryFn: () => isDemoMode() ? Promise.resolve(DEMO_TIMESERIES) : getTimeseries(period, granularity),
    staleTime: 60_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useByUser(period: Period = '30d') {
  return useQuery<UserBreakdown[]>({
    queryKey: ['analytics', 'by-user', period],
    queryFn: () => isDemoMode() ? Promise.resolve(DEMO_USERS as UserBreakdown[]) : getByUser(period),
    staleTime: 60_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useUsageSummary() {
  return useQuery<UsageSummary>({
    queryKey: ['analytics', 'usage-summary'],
    queryFn: () => getUsageSummary(),
    staleTime: 60_000,
    retry: 1,
    enabled: !isDemoMode(),
  })
}
