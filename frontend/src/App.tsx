// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PageShell } from '@/components/layout/PageShell'
import { Dashboard } from '@/pages/Dashboard'
import { Analytics } from '@/pages/Analytics'
import { Budgets } from '@/pages/Budgets'
import { ApiKeys } from '@/pages/ApiKeys'
import { Settings } from '@/pages/Settings'
import { Projects } from '@/pages/Projects'
import { ProjectDetail } from '@/pages/ProjectDetail'
import { Login } from '@/pages/Login'
import { Register } from '@/pages/Register'
import { Onboarding } from '@/pages/Onboarding'
import { Landing } from '@/pages/Landing'
import { NotFound } from '@/pages/NotFound'
import { ProxySetup } from '@/pages/ProxySetup'
import { Alerts } from '@/pages/Alerts'
import { AdminUsers } from '@/pages/AdminUsers'
import { AdminGroups } from '@/pages/AdminGroups'
import { AdminGroupDetail } from '@/pages/AdminGroupDetail'
import { AuthProvider } from '@/contexts/AuthContext'
import { apiClient } from '@/api/client'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

/**
 * Auth guard that adapts based on AUTH_MODE from the backend:
 * - "local"  → requires JWT (email+password login)
 * - "clerk"  → requires Clerk session or JWT
 * - "none"   → auto-provisions API key, no login needed
 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading')

  useEffect(() => {
    const jwt = localStorage.getItem('tb_token')
    const apiKey = localStorage.getItem('tb_api_key')

    // Already have a token — proceed
    if (jwt || apiKey) {
      setStatus('authenticated')
      return
    }

    // No token — check what auth mode the backend is configured for
    apiClient
      .get('/api/auth/config')
      .then((res) => {
        const mode = res.data?.auth_mode

        if (mode === 'none') {
          // Auto-provision a key — no login required
          apiClient
            .post('/api/setup', { name: 'default' })
            .then((setupRes) => {
              const key = setupRes.data?.raw_key
              if (key) {
                localStorage.setItem('tb_api_key', key)
                setStatus('authenticated')
              } else {
                setStatus('unauthenticated')
              }
            })
            .catch(() => setStatus('unauthenticated'))
        } else {
          // local or clerk — user must log in
          setStatus('unauthenticated')
        }
      })
      .catch(() => {
        // API unreachable — redirect to login
        setStatus('unauthenticated')
      })
  }, [])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-[#64748b]">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />
  }

  return <AuthProvider>{children}</AuthProvider>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/home" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/onboarding" element={<Onboarding />} />

          {/* Dashboard — requires auth */}
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <PageShell />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="budgets" element={<Budgets />} />
            <Route path="keys" element={<ApiKeys />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="settings" element={<Settings />} />
            <Route path="proxy" element={<ProxySetup />} />
            <Route path="admin/users" element={<AdminUsers />} />
            <Route path="admin/groups" element={<AdminGroups />} />
            <Route path="admin/groups/:id" element={<AdminGroupDetail />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
