// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { UserInfo } from '@/api/types'
import { getMe, logout as doLogout } from '@/api/auth'

interface AuthContextValue {
  user: UserInfo | null
  loading: boolean
  isAdmin: boolean
  refetch: () => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  isAdmin: false,
  refetch: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(() => {
    const token = localStorage.getItem('tb_token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    getMe()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, loading, isAdmin, refetch: fetchUser, logout: doLogout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useCurrentUser() {
  return useContext(AuthContext)
}
