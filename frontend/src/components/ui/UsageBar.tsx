// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { clsx } from 'clsx'

interface UsageBarProps {
  label: string
  current: number
  limit: number
  unit?: string
  className?: string
}

function formatValue(n: number, unit?: string): string {
  if (unit) return `${n.toLocaleString()} ${unit}`
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString()
}

export function UsageBar({ label, current, limit, unit, className }: UsageBarProps) {
  const pct = limit > 0 ? Math.min((current / limit) * 100, 100) : 0
  const isWarning = pct >= 80
  const isCritical = pct >= 95

  const barColor = isCritical
    ? 'bg-red-500'
    : isWarning
    ? 'bg-yellow-500'
    : 'bg-emerald-500'

  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      <div className="flex items-center justify-between text-xs text-[#94a3b8]">
        <span>{label}</span>
        <span>
          <span className={clsx('font-medium', isCritical ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-white')}>
            {formatValue(current, unit)}
          </span>
          <span className="text-[#64748b]"> / {formatValue(limit, unit)}</span>
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-[#1e293b] overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={current}
          aria-valuemin={0}
          aria-valuemax={limit}
          aria-label={`${label}: ${pct.toFixed(0)}%`}
        />
      </div>
    </div>
  )
}
