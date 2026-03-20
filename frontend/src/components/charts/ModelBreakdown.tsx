// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, type TooltipProps } from 'recharts'
import type { ModelBreakdown } from '@/api/types'
import { formatCurrency, formatPercent } from '@/lib/formatters'
import { getModelColor } from '@/lib/constants'

interface ModelBreakdownChartProps {
  data: ModelBreakdown[]
  height?: number
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="bg-[#1a1a24] border border-[#1e1e2e] rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs font-medium text-[#e2e8f0] mb-1">{d.name}</p>
      <p className="text-sm font-semibold text-[#e2e8f0]">{formatCurrency(d.value ?? 0)}</p>
      <p className="text-xs text-[#64748b]">{formatPercent(d.payload.percentage)}</p>
    </div>
  )
}

function CustomLegend({ payload }: { payload?: Array<{ value: string; color: string; payload: ModelBreakdown }> }) {
  if (!payload) return null
  return (
    <ul className="flex flex-col gap-1.5 mt-2">
      {payload.map((entry, i) => (
        <li key={i} className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: entry.color }} />
            <span className="text-[#64748b] truncate max-w-[120px]">{entry.value}</span>
          </div>
          <span className="text-[#e2e8f0] font-medium ml-2">{formatPercent(entry.payload.percentage)}</span>
        </li>
      ))}
    </ul>
  )
}

export function ModelBreakdownChart({ data, height = 280 }: ModelBreakdownChartProps) {
  const total = data.reduce((sum, d) => sum + d.total_cost_usd, 0)

  return (
    <div style={{ height }} className="relative">
      <ResponsiveContainer width="100%" height="70%">
        <PieChart>
          <Pie
            data={data}
            dataKey="total_cost_usd"
            nameKey="model"
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="80%"
            paddingAngle={2}
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.model}
                fill={getModelColor(entry.model, index)}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      {/* Center label */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-center" style={{ height: '70%' }}>
        <div className="text-center">
          <p className="text-xs text-[#64748b]">Total</p>
          <p className="text-base font-semibold text-[#e2e8f0]">{formatCurrency(total)}</p>
        </div>
      </div>
      {/* Legend */}
      <div className="mt-2 px-2">
        <CustomLegend
          payload={data.map((d, i) => ({
            value: d.model,
            color: getModelColor(d.model, i),
            payload: d,
          }))}
        />
      </div>
    </div>
  )
}
