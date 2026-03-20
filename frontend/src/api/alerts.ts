// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { AlertConfig, AlertConfigCreate } from './types'

export const getAlerts = () =>
  apiClient.get<AlertConfig[]>('/api/alerts').then((r) => r.data)

export const createAlert = (data: AlertConfigCreate) =>
  apiClient.post<AlertConfig>('/api/alerts', data).then((r) => r.data)

export const deleteAlert = (id: string) =>
  apiClient.delete(`/api/alerts/${id}`)

export const testAlert = (id: string) =>
  apiClient.post(`/api/alerts/${id}/test`)
