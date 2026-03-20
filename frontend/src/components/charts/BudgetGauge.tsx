// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { formatCurrency, formatPercent } from '@/lib/formatters'

interface BudgetGaugeProps {
  current: number
  limit: number
  size?: number
}

/**
 * Returns a smooth interpolated color across green -> yellow -> red
 * based on utilization percentage (0–100).
 */
function getColor(pct: number): string {
  if (pct >= 90) return '#f43f5e'  // red
  if (pct >= 75) return '#fb923c'  // orange
  if (pct >= 55) return '#f59e0b'  // amber/yellow
  return '#10b981'                  // green
}

/**
 * Returns a glow shadow color for the progress arc end-point.
 */
function getGlow(pct: number): string {
  if (pct >= 90) return 'rgba(244,63,94,0.5)'
  if (pct >= 75) return 'rgba(251,146,60,0.45)'
  if (pct >= 55) return 'rgba(245,158,11,0.45)'
  return 'rgba(16,185,129,0.45)'
}

export function BudgetGauge({ current, limit, size = 172 }: BudgetGaugeProps) {
  const pct = limit > 0 ? Math.min((current / limit) * 100, 100) : 0
  const color = getColor(pct)
  const glowColor = getGlow(pct)

  const strokeWidth = 11
  const radius = (size - strokeWidth) / 2
  const cx = size / 2
  const cy = size / 2

  // 270-degree arc, starting from bottom-left
  const startAngle = 135
  const sweepAngle = 270
  const endAngle = startAngle + sweepAngle * (pct / 100)

  function polarToCartesian(angle: number) {
    const rad = ((angle - 90) * Math.PI) / 180
    return {
      x: cx + radius * Math.cos(rad),
      y: cy + radius * Math.sin(rad),
    }
  }

  function describeArc(start: number, end: number, large: boolean) {
    const s = polarToCartesian(start)
    const e = polarToCartesian(end)
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large ? 1 : 0} 1 ${e.x} ${e.y}`
  }

  const trackEnd = startAngle + sweepAngle
  const trackLarge = sweepAngle > 180
  const progressLarge = sweepAngle * (pct / 100) > 180

  const remaining = Math.max(limit - current, 0)
  const isOverBudget = current > limit

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ overflow: 'visible' }}>
          <defs>
            {/* Gradient for the progress arc */}
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={color} stopOpacity={0.7} />
              <stop offset="100%" stopColor={color} stopOpacity={1} />
            </linearGradient>
            <filter id="gaugeGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Track ring */}
          <path
            d={describeArc(startAngle, trackEnd, trackLarge)}
            fill="none"
            stroke="#1e1e2e"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Progress arc */}
          {pct > 0 && (
            <path
              d={describeArc(startAngle, endAngle, progressLarge)}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              style={{
                transition: 'stroke 0.5s ease, d 0.5s ease',
                filter: `drop-shadow(0 0 6px ${glowColor})`,
              }}
            />
          )}
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-0.5">
          <span
            className="text-2xl font-bold tracking-tight tabular-nums"
            style={{ color, lineHeight: 1 }}
          >
            {formatPercent(pct)}
          </span>
          <span className="text-[11px] font-medium text-[#64748b] mt-0.5">used</span>
        </div>
      </div>

      {/* Spend details */}
      <div className="text-center flex flex-col gap-1">
        <p className="text-sm font-semibold text-[#e2e8f0] tabular-nums">
          {formatCurrency(current)}{' '}
          <span className="text-[#475569] font-normal">/ {formatCurrency(limit)}</span>
        </p>
        <p className="text-xs text-[#64748b]">
          {isOverBudget ? (
            <span className="text-red-400 font-medium">
              {formatCurrency(current - limit)} over budget
            </span>
          ) : (
            <span>
              {formatCurrency(remaining)} remaining
            </span>
          )}
        </p>
      </div>
    </div>
  )
}
