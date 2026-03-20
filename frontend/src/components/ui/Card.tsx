// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { clsx } from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  subValue?: string
  trend?: number
  icon?: React.ReactNode
  className?: string
  animationDelay?: string
}

export function StatCard({ label, value, subValue, trend, icon, className, animationDelay }: StatCardProps) {
  const trendPositive = trend != null && trend > 0
  const trendNegative = trend != null && trend < 0
  const trendFlat = trend != null && trend === 0

  return (
    <div
      className={clsx('card-hover flex flex-col gap-4 animate-slide-up', className)}
      style={{ animationDelay: animationDelay ?? '0ms', animationFillMode: 'both' }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-[#64748b] uppercase tracking-widest leading-tight">
          {label}
        </span>
        {icon && (
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 100%)',
              border: '1px solid rgba(99,102,241,0.15)',
              color: '#818cf8',
            }}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex flex-col gap-1">
        <span className="text-3xl font-bold text-[#e2e8f0] tracking-tight tabular-nums leading-none">
          {value}
        </span>
        {subValue && <span className="text-xs text-[#64748b] mt-0.5">{subValue}</span>}
      </div>

      {/* Trend */}
      {trend != null && (
        <div
          className={clsx(
            'flex items-center gap-1.5 text-xs font-semibold',
            trendPositive && 'text-emerald-400',
            trendNegative && 'text-red-400',
            trendFlat && 'text-[#64748b]'
          )}
        >
          {trendPositive && <TrendingUp size={12} />}
          {trendNegative && <TrendingDown size={12} />}
          {trendFlat && <Minus size={12} />}
          <span>
            {trendPositive ? '+' : ''}
            {trend.toFixed(1)}% vs last period
          </span>
        </div>
      )}
    </div>
  )
}

interface CardProps {
  children: React.ReactNode
  className?: string
  title?: string
  subtitle?: string
  action?: React.ReactNode
}

export function Card({ children, className, title, subtitle, action }: CardProps) {
  return (
    <div className={clsx('card animate-fade-in', className)}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-[#94a3b8] uppercase tracking-widest leading-tight">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[#64748b] mt-1">{subtitle}</p>
            )}
          </div>
          {action && <div className="flex-shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </div>
  )
}
