// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  type TooltipProps,
} from 'recharts'
import type { TimeseriesPoint } from '@/api/types'
import { formatCurrency, formatDate } from '@/lib/formatters'

interface SpendOverTimeProps {
  data: TimeseriesPoint[]
  height?: number
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null

  const cost = payload[0]?.value ?? 0
  const requests = payload[1]?.value

  return (
    <div
      style={{
        background: 'linear-gradient(160deg, #1e1e2e 0%, #161622 100%)',
        border: '1px solid #2a2a3d',
        borderRadius: 10,
        padding: '10px 14px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      <p
        style={{
          fontSize: 11,
          color: '#64748b',
          marginBottom: 6,
          fontWeight: 500,
          letterSpacing: '0.02em',
        }}
      >
        {formatDate(label)}
      </p>
      <p
        style={{
          fontSize: 15,
          fontWeight: 700,
          color: '#e2e8f0',
          letterSpacing: '-0.02em',
          lineHeight: 1,
        }}
      >
        {formatCurrency(cost)}
      </p>
      {requests != null && (
        <p
          style={{
            fontSize: 11,
            color: '#64748b',
            marginTop: 4,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#818cf8',
            }}
          />
          {String(requests)} requests
        </p>
      )}
    </div>
  )
}

export function SpendOverTime({ data, height = 280 }: SpendOverTimeProps) {
  const chartData = data.map((d) => ({
    ...d,
    date: d.timestamp,
    cost: d.cost_usd,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 10, right: 4, left: 0, bottom: 0 }}>
        <defs>
          {/* Primary gradient fill */}
          <linearGradient id="costGradientFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#818cf8" stopOpacity={0.22} />
            <stop offset="45%"  stopColor="#6366f1" stopOpacity={0.1} />
            <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
          {/* Glow filter on the stroke */}
          <filter id="lineGlow" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,30,46,0.8)" vertical={false} />

        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
          axisLine={false}
          tickLine={false}
          tickMargin={8}
        />
        <YAxis
          tickFormatter={(v) => `$${v}`}
          tick={{ fill: '#475569', fontSize: 11, fontFamily: 'Inter, sans-serif' }}
          axisLine={false}
          tickLine={false}
          width={48}
        />

        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#2a2a3d', strokeWidth: 1 }} />

        <Area
          type="monotone"
          dataKey="cost"
          stroke="#818cf8"
          strokeWidth={2}
          fill="url(#costGradientFill)"
          dot={false}
          activeDot={{
            r: 5,
            fill: '#0a0a0f',
            stroke: '#818cf8',
            strokeWidth: 2.5,
            filter: 'url(#lineGlow)',
          }}
          style={{ filter: 'url(#lineGlow)' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
