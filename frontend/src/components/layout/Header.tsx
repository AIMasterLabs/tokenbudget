// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { ChevronDown } from 'lucide-react'
import { PERIOD_OPTIONS } from '@/lib/constants'
import type { Period } from '@/api/types'

interface HeaderProps {
  title: string
  period?: Period
  onPeriodChange?: (period: Period) => void
  action?: React.ReactNode
}

export function Header({ title, period, onPeriodChange, action }: HeaderProps) {
  return (
    <header
      className="h-14 flex items-center justify-between px-6 sticky top-0 z-30"
      style={{
        background: 'rgba(10,10,15,0.8)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid #1e1e2e',
      }}
    >
      <h1 className="text-sm font-semibold text-[#c4c4e0] tracking-tight">{title}</h1>

      {action && <div className="flex items-center">{action}</div>}

      {period && onPeriodChange && (
        <div className="relative">
          <select
            value={period}
            onChange={(e) => onPeriodChange(e.target.value as Period)}
            className="appearance-none text-[#c4c4e0] text-xs font-medium rounded-lg pl-3 pr-7 py-1.5 cursor-pointer"
            style={{
              background: 'rgba(26,26,36,0.8)',
              border: '1px solid #2a2a3d',
              outline: 'none',
              transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = '#6366f1'
              e.currentTarget.style.boxShadow = '0 0 0 3px rgba(99,102,241,0.15)'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#2a2a3d'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} style={{ background: '#1a1a24' }}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown
            size={12}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[#64748b] pointer-events-none"
          />
        </div>
      )}
    </header>
  )
}
