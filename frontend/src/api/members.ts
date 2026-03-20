// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type { ProjectMember } from './types'

export const getProjectMembers = (projectId: string) =>
  apiClient
    .get<ProjectMember[]>(`/api/projects/${projectId}/members`)
    .then((r) => r.data)

export const addProjectMember = (projectId: string, userId: string, role: string) =>
  apiClient
    .post<ProjectMember>(`/api/projects/${projectId}/members`, { user_id: userId, role })
    .then((r) => r.data)

export const removeProjectMember = (projectId: string, userId: string) =>
  apiClient.delete(`/api/projects/${projectId}/members/${userId}`)
