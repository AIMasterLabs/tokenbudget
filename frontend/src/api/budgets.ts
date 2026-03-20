// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { Budget, BudgetCreatePayload } from './types'

export async function listBudgets(): Promise<Budget[]> {
  const { data } = await apiClient.get('/api/budgets')
  return data
}

export async function createBudget(payload: BudgetCreatePayload): Promise<Budget> {
  const { data } = await apiClient.post('/api/budgets', payload)
  return data
}

export async function updateBudget(id: string, payload: Partial<BudgetCreatePayload>): Promise<Budget> {
  const { data } = await apiClient.put(`/api/budgets/${id}`, payload)
  return data
}

export async function deleteBudget(id: string): Promise<void> {
  await apiClient.delete(`/api/budgets/${id}`)
}

export async function getBudgetStatus(id: string): Promise<Budget> {
  const { data } = await apiClient.get(`/api/budgets/${id}/status`)
  return data
}
