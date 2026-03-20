// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
  rounded?: 'sm' | 'md' | 'lg' | 'full'
}

export function Skeleton({ className, width, height, rounded = 'md' }: SkeletonProps) {
  const roundedClass = {
    sm: 'rounded',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  }[rounded]

  return (
    <div
      className={clsx('skeleton', roundedClass, className)}
      style={{ width, height }}
    />
  )
}

/** Pre-built skeleton layout for a StatCard */
export function StatCardSkeleton({ animationDelay }: { animationDelay?: string }) {
  return (
    <div
      className="card flex flex-col gap-4 animate-fade-in"
      style={{ animationDelay: animationDelay ?? '0ms', animationFillMode: 'both' }}
    >
      <div className="flex items-start justify-between">
        <Skeleton height={10} width={80} />
        <Skeleton height={32} width={32} rounded="lg" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton height={36} width={110} rounded="md" />
        <Skeleton height={10} width={60} />
      </div>
    </div>
  )
}

/** Pre-built skeleton for a chart area */
export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div className="flex flex-col gap-3 animate-fade-in">
      {/* Y-axis + bars */}
      <div className="flex items-end gap-2 w-full" style={{ height }}>
        <div className="flex flex-col gap-2 w-8 flex-shrink-0">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} height={10} width={28} />
          ))}
        </div>
        <div className="flex-1 flex items-end gap-1.5">
          {[...Array(12)].map((_, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              rounded="sm"
              height={`${20 + Math.abs(Math.sin(i * 1.3)) * 70}%`}
            />
          ))}
        </div>
      </div>
      {/* X-axis labels */}
      <div className="flex gap-1.5 pl-10">
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} height={8} width={28} className="flex-1" />
        ))}
      </div>
    </div>
  )
}
