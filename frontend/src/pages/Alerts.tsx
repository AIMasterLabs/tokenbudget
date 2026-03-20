// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell, Plus, Trash2, Send, X } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { getAlerts, createAlert, deleteAlert, testAlert } from '@/api/alerts'
import type { AlertChannel, AlertConfigCreate, Budget } from '@/api/types'
import { apiClient } from '@/api/client'

export function Alerts() {
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: getAlerts,
  })

  const { data: budgets } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => apiClient.get<Budget[]>('/api/budgets').then((r) => r.data),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alerts'] }),
  })

  const testMutation = useMutation({
    mutationFn: testAlert,
  })

  return (
    <div className="flex flex-col min-h-full">
      <Header title="Alerts" />
      <div className="p-6 flex flex-col gap-6">

        {/* Actions */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-[#64748b]">
            Configure notifications when budgets hit spend thresholds.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Plus size={15} />
            New Alert
          </button>
        </div>

        {/* Create dialog */}
        {showCreate && (
          <CreateAlertForm
            budgets={budgets ?? []}
            onClose={() => setShowCreate(false)}
          />
        )}

        {/* Loading / Error */}
        {isLoading && (
          <p className="text-sm text-[#64748b] animate-pulse">Loading alerts...</p>
        )}
        {error && (
          <p className="text-sm text-red-400">
            Failed to load alerts. Make sure the API server is running.
          </p>
        )}

        {/* Empty */}
        {!isLoading && !error && alerts?.length === 0 && (
          <Card>
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Bell size={32} className="text-[#475569]" />
              <p className="text-sm text-[#64748b]">No alerts configured yet.</p>
            </div>
          </Card>
        )}

        {/* Alert list */}
        {alerts && alerts.length > 0 && (
          <div className="flex flex-col gap-3">
            {alerts.map((a) => (
              <Card key={a.id}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#6366f1]/10 flex items-center justify-center flex-shrink-0">
                      <Bell size={14} className="text-[#818cf8]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#e2e8f0] capitalize">
                        {a.channel} alert
                      </p>
                      <p className="text-xs text-[#64748b] font-mono truncate max-w-[320px]">
                        {a.url}
                      </p>
                      <p className="text-xs text-[#475569] mt-0.5">
                        Thresholds: {a.thresholds.map((t) => `${t}%`).join(', ')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => testMutation.mutate(a.id)}
                      disabled={testMutation.isPending}
                      className="p-2 rounded-lg text-[#64748b] hover:text-[#818cf8] hover:bg-[#6366f1]/10 transition-colors"
                      title="Send test alert"
                    >
                      <Send size={14} />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(a.id)}
                      disabled={deleteMutation.isPending}
                      className="p-2 rounded-lg text-[#64748b] hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      title="Delete alert"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Create Alert Form ─────────────────────────────────────────────────────────

function CreateAlertForm({
  budgets,
  onClose,
}: {
  budgets: Budget[]
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [channel, setChannel] = useState<AlertChannel>('slack')
  const [url, setUrl] = useState('')
  const [budgetId, setBudgetId] = useState('')
  const [thresholds, setThresholds] = useState('50,80,100')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createAlert,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
      onClose()
    },
    onError: () => setError('Failed to create alert.'),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!url.trim()) { setError('URL is required.'); return }
    if (!budgetId) { setError('Select a budget.'); return }

    const parsed = thresholds
      .split(',')
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !isNaN(n) && n > 0 && n <= 100)

    if (parsed.length === 0) {
      setError('Enter at least one valid threshold (1-100).')
      return
    }

    const payload: AlertConfigCreate = {
      channel,
      url: url.trim(),
      budget_id: budgetId,
      thresholds: parsed,
    }
    mutation.mutate(payload)
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-[#e2e8f0]">New Alert</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-[#64748b] hover:text-[#e2e8f0] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Channel */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#64748b]">Channel</label>
          <select
            className="input text-sm"
            value={channel}
            onChange={(e) => setChannel(e.target.value as AlertChannel)}
          >
            <option value="slack">Slack</option>
            <option value="webhook">Webhook</option>
          </select>
        </div>

        {/* URL */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#64748b]">
            {channel === 'slack' ? 'Slack Webhook URL' : 'Webhook URL'}
          </label>
          <input
            className="input text-sm font-mono"
            placeholder="https://hooks.slack.com/services/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>

        {/* Budget */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#64748b]">Budget</label>
          <select
            className="input text-sm"
            value={budgetId}
            onChange={(e) => setBudgetId(e.target.value)}
          >
            <option value="">Select a budget...</option>
            {budgets.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name ?? `$${b.amount_usd} / ${b.period}`}
              </option>
            ))}
          </select>
        </div>

        {/* Thresholds */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#64748b]">
            Thresholds (% comma separated)
          </label>
          <input
            className="input text-sm"
            placeholder="50,80,100"
            value={thresholds}
            onChange={(e) => setThresholds(e.target.value)}
          />
        </div>

        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="btn-primary flex items-center justify-center gap-2 text-sm"
        >
          {mutation.isPending ? 'Creating...' : 'Create Alert'}
        </button>
      </form>
    </Card>
  )
}
