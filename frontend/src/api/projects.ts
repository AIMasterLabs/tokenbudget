// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { AnalyticsSummary, TimeseriesPoint } from './types'

export interface Project {
  id: string
  name: string
  slug: string
  description: string | null
  color: string
  is_active: boolean
  created_at: string
}

export interface ProjectCreate {
  name: string
  description?: string
  color?: string
}

export const getProjects = () =>
  apiClient.get<Project[]>('/api/projects').then((r) => r.data)

export const getProject = (id: string) =>
  apiClient.get<Project>(`/api/projects/${id}`).then((r) => r.data)

export const createProject = (data: ProjectCreate) =>
  apiClient.post<Project>('/api/projects', data).then((r) => r.data)

export const updateProject = (id: string, data: Partial<ProjectCreate>) =>
  apiClient.put<Project>(`/api/projects/${id}`, data).then((r) => r.data)

export const deleteProject = (id: string) =>
  apiClient.delete(`/api/projects/${id}`)

export const getProjectAnalytics = (id: string, period = '30d') =>
  apiClient
    .get<AnalyticsSummary>(`/api/projects/${id}/analytics/summary?period=${period}`)
    .then((r) => r.data)

export const getProjectTimeseries = (id: string, period = '30d') =>
  apiClient
    .get<TimeseriesPoint[]>(`/api/projects/${id}/analytics/timeseries?period=${period}`)
    .then((r) => r.data)
