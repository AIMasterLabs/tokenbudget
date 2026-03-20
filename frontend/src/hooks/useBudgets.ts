// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listBudgets, createBudget, deleteBudget } from '@/api/budgets'
import { isDemoMode, DEMO_BUDGETS } from '@/lib/demoData'
import type { BudgetCreatePayload } from '@/api/types'

export function useBudgets() {
  return useQuery({
    queryKey: ['budgets'],
    queryFn: () => isDemoMode() ? DEMO_BUDGETS : listBudgets(),
    staleTime: 30_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useCreateBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BudgetCreatePayload) => createBudget(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budgets'] })
    },
  })
}

export function useDeleteBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteBudget(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budgets'] })
    },
  })
}
