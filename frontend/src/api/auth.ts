// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { AuthResponse, UserInfo } from './types'

export const login = (email: string, password: string) =>
  apiClient
    .post<AuthResponse>('/api/auth/login', { email, password })
    .then((r) => {
      localStorage.setItem('tb_token', r.data.token)
      return r.data
    })

export const register = (email: string, password: string, name: string) =>
  apiClient
    .post<AuthResponse>('/api/auth/register', { email, password, name })
    .then((r) => {
      localStorage.setItem('tb_token', r.data.token)
      return r.data
    })

export const getMe = () =>
  apiClient.get<UserInfo>('/api/auth/me').then((r) => r.data)

export const changePassword = (currentPassword: string, newPassword: string) =>
  apiClient
    .post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    .then((r) => r.data)

export const logout = () => {
  localStorage.removeItem('tb_token')
  localStorage.removeItem('tb_api_key')
  window.location.href = '/login'
}
