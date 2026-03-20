// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { DollarSign, Activity, Cpu, Users, Download, FileText } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { StatCard, Card } from '@/components/ui/Card'
import { SpendOverTime } from '@/components/charts/SpendOverTime'
import { ModelBreakdownChart } from '@/components/charts/ModelBreakdown'
import { UserBreakdownChart } from '@/components/charts/UserBreakdown'
import { EmptyState } from '@/components/ui/EmptyState'
import { useSummary, useByModel, useTimeseries, useByUser } from '@/hooks/useAnalytics'
import { formatCurrency, formatNumber, formatTokens } from '@/lib/formatters'
import { exportCSV, exportPDF } from '@/api/analytics'
import type { Period } from '@/api/types'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function Analytics() {
  const [period, setPeriod] = useState<Period>('30d')
  const [exporting, setExporting] = useState<'csv' | 'pdf' | null>(null)

  async function handleExport(format: 'csv' | 'pdf') {
    setExporting(format)
    try {
      const blob = format === 'csv' ? await exportCSV(period) : await exportPDF(period)
      const ext = format === 'csv' ? 'csv' : 'pdf'
      downloadBlob(blob, `tokenbudget-report-${period}.${ext}`)
    } catch (e) {
      console.error('Export failed:', e)
    } finally {
      setExporting(null)
    }
  }

  const summary = useSummary(period)
  const timeseries = useTimeseries(period)
  const byModel = useByModel(period)
  const byUser = useByUser(period)

  const s = summary.data

  return (
    <div className="flex flex-col min-h-full">
      <Header title="Analytics" period={period} onPeriodChange={setPeriod} />

      <div className="p-6 flex flex-col gap-6">
        {/* Export buttons */}
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting !== null}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#1a1a24] hover:bg-[#1e1e2e] text-[#e2e8f0] text-xs font-medium transition-colors disabled:opacity-50"
          >
            <Download size={14} />
            {exporting === 'csv' ? 'Exporting...' : 'Export CSV'}
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exporting !== null}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#1e1e2e] bg-[#1a1a24] hover:bg-[#1e1e2e] text-[#e2e8f0] text-xs font-medium transition-colors disabled:opacity-50"
          >
            <FileText size={14} />
            {exporting === 'pdf' ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            label="Total Spend"
            value={s ? formatCurrency(s.total_cost_usd) : '—'}
            icon={<DollarSign size={16} />}
          />
          <StatCard
            label="Requests"
            value={s ? formatNumber(s.total_requests) : '—'}
            icon={<Activity size={16} />}
          />
          <StatCard
            label="Input Tokens"
            value={s ? formatTokens(s.total_input_tokens) : '—'}
            icon={<Cpu size={16} />}
          />
          <StatCard
            label="Output Tokens"
            value={s ? formatTokens(s.total_output_tokens) : '—'}
            icon={<Users size={16} />}
          />
        </div>

        {/* Spend over time */}
        <Card title="Spend Over Time">
          {timeseries.isLoading && (
            <div className="flex items-center justify-center h-64 text-[#64748b] text-sm">Loading...</div>
          )}
          {timeseries.data && timeseries.data.length > 0 ? (
            <SpendOverTime data={timeseries.data} height={300} />
          ) : (
            !timeseries.isLoading && <EmptyState title="No timeseries data" />
          )}
        </Card>

        {/* Charts row */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card title="By Model">
            {byModel.isLoading && (
              <div className="flex items-center justify-center h-64 text-[#64748b] text-sm">Loading...</div>
            )}
            {byModel.data && byModel.data.length > 0 ? (
              <ModelBreakdownChart data={byModel.data} height={320} />
            ) : (
              !byModel.isLoading && <EmptyState title="No model data" />
            )}
          </Card>

          <Card title="By User">
            {byUser.isLoading && (
              <div className="flex items-center justify-center h-64 text-[#64748b] text-sm">Loading...</div>
            )}
            {byUser.data && byUser.data.length > 0 ? (
              <UserBreakdownChart data={byUser.data} height={320} />
            ) : (
              !byUser.isLoading && (
                <EmptyState
                  title="No user data"
                  description="User breakdown appears when requests include user IDs."
                />
              )
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
