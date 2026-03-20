// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  type TooltipProps,
} from 'recharts'
import type { UserBreakdown } from '@/api/types'
import { formatCurrency } from '@/lib/formatters'

interface UserBreakdownChartProps {
  data: UserBreakdown[]
  height?: number
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-[#1a1a24] border border-[#1e1e2e] rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs text-[#64748b] mb-1">{label}</p>
      <p className="text-sm font-semibold text-[#e2e8f0]">{formatCurrency(payload[0].value ?? 0)}</p>
    </div>
  )
}

export function UserBreakdownChart({ data, height = 280 }: UserBreakdownChartProps) {
  const sorted = [...data].sort((a, b) => b.total_cost_usd - a.total_cost_usd).slice(0, 10)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 0, right: 8, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={(v) => `$${v}`}
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="user_id"
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={80}
          tickFormatter={(v: string) => (v.length > 10 ? v.slice(0, 10) + '…' : v)}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1a1a24' }} />
        <Bar dataKey="total_cost_usd" radius={[0, 4, 4, 0]}>
          {sorted.map((_entry, index) => (
            <Cell
              key={index}
              fill={index === 0 ? '#6366f1' : '#1a1a24'}
              stroke={index === 0 ? '#818cf8' : '#1e1e2e'}
              strokeWidth={1}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
