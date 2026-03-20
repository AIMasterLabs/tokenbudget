// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { Link } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'

export function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] px-4">
      <div className="text-center animate-scale-in">
        <div className="w-16 h-16 rounded-2xl bg-[var(--danger)]/10 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-8 h-8 text-[var(--danger)]" />
        </div>
        <h1 className="text-6xl font-extrabold text-[var(--text)] mb-2">404</h1>
        <p className="text-lg text-[var(--muted)] mb-8">This page doesn't exist.</p>
        <Link to="/" className="btn-primary inline-flex items-center gap-2">
          <Home className="w-4 h-4" />
          Go Home
        </Link>
      </div>
    </div>
  )
}
