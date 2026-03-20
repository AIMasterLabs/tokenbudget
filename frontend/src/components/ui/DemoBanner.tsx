// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { Link } from 'react-router-dom'
import { BarChart3, ArrowRight, X } from 'lucide-react'
import { isDemoMode, disableDemoMode } from '@/lib/demoData'

export function DemoBanner() {
  if (!isDemoMode()) return null

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2.5 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2 text-sm text-amber-300">
        <BarChart3 className="w-4 h-4 flex-shrink-0" />
        <span>
          <strong>Demo Mode</strong> — You're viewing sample data.{' '}
          <Link to="/login" className="underline hover:text-amber-200 inline-flex items-center gap-1">
            Get Started <ArrowRight className="w-3 h-3" />
          </Link>{' '}
          to track real usage.
        </span>
      </div>
      <button
        onClick={() => { disableDemoMode(); window.location.href = '/' }}
        className="text-amber-400/60 hover:text-amber-300 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
