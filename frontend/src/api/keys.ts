// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { ApiKeyResponse, ApiKeyCreateResponse } from './types'

export async function listKeys(): Promise<ApiKeyResponse[]> {
  const { data } = await apiClient.get('/api/keys')
  return data
}

export async function createKey(name: string): Promise<ApiKeyCreateResponse> {
  const { data } = await apiClient.post('/api/keys', { name })
  return data
}

export async function deleteKey(id: string): Promise<void> {
  await apiClient.delete(`/api/keys/${id}`)
}
