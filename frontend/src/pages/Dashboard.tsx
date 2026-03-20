// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { DollarSign, Activity, Zap, Clock } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { StatCard, Card } from '@/components/ui/Card'
import { StatCardSkeleton, ChartSkeleton } from '@/components/ui/Skeleton'
import { SpendOverTime } from '@/components/charts/SpendOverTime'
import { ModelBreakdownChart } from '@/components/charts/ModelBreakdown'
import { BudgetGauge } from '@/components/charts/BudgetGauge'
import { EmptyState } from '@/components/ui/EmptyState'
import { UsageBar } from '@/components/ui/UsageBar'
import { useSummary, useByModel, useTimeseries, useUsageSummary } from '@/hooks/useAnalytics'
import { useBudgets } from '@/hooks/useBudgets'
import { formatCurrency, formatNumber, formatLatency } from '@/lib/formatters'
import type { Period } from '@/api/types'

export function Dashboard() {
  const [period, setPeriod] = useState<Period>('30d')

  const summary = useSummary(period)
  const timeseries = useTimeseries(period)
  const byModel = useByModel(period)
  const budgets = useBudgets()

  const usage = useUsageSummary()
  const s = summary.data
  const firstBudget = budgets.data?.[0]

  return (
    <div className="flex flex-col min-h-full">
      <Header title="Dashboard" period={period} onPeriodChange={setPeriod} />

      <div className="p-6 flex flex-col gap-6">

        {/* ── Stat Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {summary.isLoading ? (
            <>
              <StatCardSkeleton animationDelay="0ms" />
              <StatCardSkeleton animationDelay="60ms" />
              <StatCardSkeleton animationDelay="120ms" />
              <StatCardSkeleton animationDelay="180ms" />
            </>
          ) : (
            <>
              <StatCard
                label="Total Spend"
                value={s ? formatCurrency(s.total_cost_usd) : '—'}
                icon={<DollarSign size={15} />}
                animationDelay="0ms"
              />
              <StatCard
                label="Total Requests"
                value={s ? formatNumber(s.total_requests) : '—'}
                icon={<Activity size={15} />}
                animationDelay="60ms"
              />
              <StatCard
                label="Avg Cost / Request"
                value={s ? formatCurrency(s.avg_cost_per_request) : '—'}
                icon={<Zap size={15} />}
                animationDelay="120ms"
              />
              <StatCard
                label="Avg Latency"
                value={s ? formatLatency(s.avg_latency_ms) : '—'}
                icon={<Clock size={15} />}
                animationDelay="180ms"
              />
            </>
          )}
        </div>

        {/* ── Usage ── */}
        {usage.data && (
          <div
            className="animate-slide-up"
            style={{ animationDelay: '40ms', animationFillMode: 'both' }}
          >
            <Card
              title="Usage"
              subtitle="Resets monthly"
            >
              <div className="flex flex-col gap-4 pt-1">
                <UsageBar
                  label="Events this month"
                  current={usage.data.events_this_month}
                  limit={usage.data.events_limit}
                />
                <UsageBar
                  label="API keys"
                  current={usage.data.active_keys}
                  limit={usage.data.keys_limit}
                />
              </div>
            </Card>
          </div>
        )}

        {/* ── Spend Over Time ── */}
        <div
          className="animate-slide-up"
          style={{ animationDelay: '100ms', animationFillMode: 'both' }}
        >
          <Card title="Spend Over Time">
            {timeseries.isLoading && <ChartSkeleton height={280} />}
            {timeseries.isError && (
              <EmptyState title="Could not load chart" description="Make sure the API is running." />
            )}
            {timeseries.data && timeseries.data.length === 0 && (
              <EmptyState title="No spend data yet" description="Data will appear once you start tracking requests." />
            )}
            {timeseries.data && timeseries.data.length > 0 && (
              <SpendOverTime data={timeseries.data} />
            )}
          </Card>
        </div>

        {/* ── Bottom Row ── */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Model Breakdown */}
          <div
            className="animate-slide-up"
            style={{ animationDelay: '160ms', animationFillMode: 'both' }}
          >
            <Card title="Model Breakdown">
              {byModel.isLoading && <ChartSkeleton height={264} />}
              {byModel.isError && (
                <EmptyState title="Could not load breakdown" />
              )}
              {byModel.data && byModel.data.length === 0 && (
                <EmptyState title="No model data yet" />
              )}
              {byModel.data && byModel.data.length > 0 && (
                <ModelBreakdownChart data={byModel.data} />
              )}
            </Card>
          </div>

          {/* Budget Status */}
          <div
            className="animate-slide-up"
            style={{ animationDelay: '220ms', animationFillMode: 'both' }}
          >
            <Card title="Budget Status">
              {budgets.isLoading && (
                <div className="flex flex-col items-center gap-4 py-6">
                  <div className="skeleton rounded-full" style={{ width: 160, height: 160 }} />
                  <div className="flex flex-col items-center gap-2">
                    <div className="skeleton rounded-md" style={{ width: 100, height: 12 }} />
                    <div className="skeleton rounded-md" style={{ width: 70, height: 10 }} />
                  </div>
                </div>
              )}
              {!budgets.isLoading && !firstBudget && (
                <EmptyState
                  title="No budgets set"
                  description="Create a budget to track your AI spend limits."
                />
              )}
              {firstBudget && (
                <div className="flex flex-col items-center py-4 gap-1">
                  <BudgetGauge
                    current={firstBudget.current_spend_usd}
                    limit={firstBudget.amount_usd}
                  />
                  <p className="text-xs text-[#64748b] mt-2">
                    <span className="capitalize">{firstBudget.period}</span> budget
                    {' · '}
                    <span className={firstBudget.is_active ? 'text-emerald-400' : 'text-[#64748b]'}>
                      {firstBudget.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </p>
                </div>
              )}
            </Card>
          </div>
        </div>

      </div>
    </div>
  )
}
