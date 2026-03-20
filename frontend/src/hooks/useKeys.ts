// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listKeys, createKey, deleteKey } from '@/api/keys'
import { isDemoMode, DEMO_KEYS } from '@/lib/demoData'

export function useKeys() {
  return useQuery({
    queryKey: ['keys'],
    queryFn: () => isDemoMode() ? DEMO_KEYS : listKeys(),
    staleTime: 30_000,
    retry: isDemoMode() ? 0 : 1,
  })
}

export function useCreateKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createKey(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['keys'] })
    },
  })
}

export function useDeleteKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteKey(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['keys'] })
    },
  })
}
