// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { UserInfo } from './types'

export const listUsers = () =>
  apiClient.get<UserInfo[]>('/api/admin/users').then((r) => r.data)

export const createUser = (
  email: string,
  password: string,
  name: string,
  role: string,
  department?: string,
) =>
  apiClient
    .post<UserInfo>('/api/auth/register', { email, password, name, role, department })
    .then((r) => r.data)

export const deactivateUser = (id: string) =>
  apiClient.delete(`/api/admin/users/${id}`).then((r) => r.data)
