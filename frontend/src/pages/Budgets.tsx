// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Plus, Trash2, Target } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { BudgetGauge } from '@/components/charts/BudgetGauge'
import { EmptyState } from '@/components/ui/EmptyState'
import { useBudgets, useCreateBudget, useDeleteBudget } from '@/hooks/useBudgets'
import { formatCurrency } from '@/lib/formatters'

interface CreateBudgetForm {
  name: string
  amount_usd: string
  period: string
  alert_thresholds: string
}

const defaultForm: CreateBudgetForm = {
  name: '',
  amount_usd: '',
  period: 'monthly',
  alert_thresholds: '80,90,100',
}

export function Budgets() {
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState<CreateBudgetForm>(defaultForm)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const budgets = useBudgets()
  const createBudget = useCreateBudget()
  const deleteBudget = useDeleteBudget()

  function handleCreate() {
    const thresholds = form.alert_thresholds
      .split(',')
      .map((t) => parseFloat(t.trim()))
      .filter((t) => !isNaN(t))

    createBudget.mutate(
      {
        name: form.name || undefined,
        amount_usd: parseFloat(form.amount_usd),
        period: form.period,
        alert_thresholds: thresholds,
      },
      {
        onSuccess: () => {
          setModalOpen(false)
          setForm(defaultForm)
        },
      }
    )
  }

  function handleDelete(id: string) {
    deleteBudget.mutate(id, {
      onSuccess: () => setDeleteId(null),
    })
  }

  return (
    <div className="flex flex-col min-h-full">
      <Header title="Budgets" />

      <div className="p-6 flex flex-col gap-6">
        {/* Actions */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-[#64748b]">
            {budgets.data?.length ?? 0} budget{budgets.data?.length !== 1 ? 's' : ''} configured
          </p>
          <button className="btn-primary flex items-center gap-2" onClick={() => setModalOpen(true)}>
            <Plus size={16} />
            Create Budget
          </button>
        </div>

        {/* Budget cards */}
        {budgets.isLoading && (
          <div className="text-center text-[#64748b] py-16">Loading...</div>
        )}

        {!budgets.isLoading && (!budgets.data || budgets.data.length === 0) && (
          <EmptyState
            icon={<Target size={24} />}
            title="No budgets yet"
            description="Create a budget to monitor and control your AI spending."
            action={
              <button className="btn-primary flex items-center gap-2" onClick={() => setModalOpen(true)}>
                <Plus size={16} />
                Create your first budget
              </button>
            }
          />
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {budgets.data?.map((budget) => (
            <Card key={budget.id} className="flex flex-col gap-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-[#e2e8f0]">
                    {budget.name || `Budget ${budget.id.slice(0, 8)}`}
                  </h3>
                  <p className="text-xs text-[#64748b] mt-0.5 capitalize">{budget.period}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={budget.is_active ? 'success' : 'neutral'}>
                    {budget.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                  <button
                    onClick={() => setDeleteId(budget.id)}
                    className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                    title="Delete budget"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <BudgetGauge
                current={budget.current_spend_usd}
                limit={budget.amount_usd}
                size={140}
              />

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#1a1a24] rounded-lg p-3">
                  <p className="text-[#64748b]">Spent</p>
                  <p className="text-[#e2e8f0] font-semibold">{formatCurrency(budget.current_spend_usd)}</p>
                </div>
                <div className="bg-[#1a1a24] rounded-lg p-3">
                  <p className="text-[#64748b]">Limit</p>
                  <p className="text-[#e2e8f0] font-semibold">{formatCurrency(budget.amount_usd)}</p>
                </div>
              </div>

              {budget.alert_thresholds.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {budget.alert_thresholds.map((t) => (
                    <Badge key={t} variant="warning">{t}%</Badge>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Create modal */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Create Budget">
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-[#64748b] mb-1.5">Name (optional)</label>
            <input
              className="input"
              placeholder="e.g. Monthly production budget"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#64748b] mb-1.5">Limit (USD)</label>
            <input
              className="input"
              type="number"
              placeholder="e.g. 100"
              value={form.amount_usd}
              onChange={(e) => setForm((f) => ({ ...f, amount_usd: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#64748b] mb-1.5">Period</label>
            <select
              className="input"
              value={form.period}
              onChange={(e) => setForm((f) => ({ ...f, period: e.target.value }))}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-[#64748b] mb-1.5">
              Alert Thresholds (%)
            </label>
            <input
              className="input"
              placeholder="e.g. 80,90,100"
              value={form.alert_thresholds}
              onChange={(e) => setForm((f) => ({ ...f, alert_thresholds: e.target.value }))}
            />
            <p className="text-xs text-[#64748b] mt-1">Comma-separated percentages</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              className="btn-primary flex-1 disabled:opacity-50"
              onClick={handleCreate}
              disabled={!form.amount_usd || createBudget.isPending}
            >
              {createBudget.isPending ? 'Creating...' : 'Create Budget'}
            </button>
            <button className="btn-ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </button>
          </div>
          {createBudget.isError && (
            <p className="text-xs text-red-400">Failed to create budget. Check your API connection.</p>
          )}
        </div>
      </Modal>

      {/* Delete confirm modal */}
      <Modal open={deleteId !== null} onClose={() => setDeleteId(null)} title="Delete Budget">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[#64748b]">Are you sure you want to delete this budget? This cannot be undone.</p>
          <div className="flex gap-3">
            <button
              className="flex-1 bg-red-500 hover:bg-red-600 text-white font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              onClick={() => deleteId && handleDelete(deleteId)}
              disabled={deleteBudget.isPending}
            >
              {deleteBudget.isPending ? 'Deleting...' : 'Delete'}
            </button>
            <button className="btn-ghost" onClick={() => setDeleteId(null)}>Cancel</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
