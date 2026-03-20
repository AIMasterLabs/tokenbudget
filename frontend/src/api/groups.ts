// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import type {
  Group,
  GroupDetail,
  GroupMember,
  GroupProjectAccess,
  Permission,
  BulkUserCreate,
  BulkUserResult,
} from './types'

// ── Group CRUD ─────────────────────────────────────────────────────────────

export const listGroups = () =>
  apiClient.get<Group[]>('/api/groups').then((r) => r.data)

export const getGroup = (id: string) =>
  apiClient.get<GroupDetail>(`/api/groups/${id}`).then((r) => r.data)

export const createGroup = (name: string, description: string) =>
  apiClient.post<Group>('/api/groups', { name, description }).then((r) => r.data)

// ── Members ────────────────────────────────────────────────────────────────

export const addMember = (groupId: string, userId: string) =>
  apiClient
    .post<GroupMember>(`/api/groups/${groupId}/members`, { user_id: userId })
    .then((r) => r.data)

export const addMembersBulk = (groupId: string, userIds: string[]) =>
  apiClient
    .post<GroupMember[]>(`/api/groups/${groupId}/members/bulk`, { user_ids: userIds })
    .then((r) => r.data)

export const removeMember = (groupId: string, userId: string) =>
  apiClient.delete(`/api/groups/${groupId}/members/${userId}`)

// ── Project Access ─────────────────────────────────────────────────────────

export const addProjectAccess = (
  groupId: string,
  projectId: string,
  permissions: Permission[],
) =>
  apiClient
    .post<GroupProjectAccess>(`/api/groups/${groupId}/projects`, {
      project_id: projectId,
      permissions,
    })
    .then((r) => r.data)

export const updateProjectPermissions = (
  groupId: string,
  projectId: string,
  permissions: Permission[],
) =>
  apiClient
    .put<GroupProjectAccess>(`/api/groups/${groupId}/projects/${projectId}`, {
      permissions,
    })
    .then((r) => r.data)

export const removeProjectAccess = (groupId: string, projectId: string) =>
  apiClient.delete(`/api/groups/${groupId}/projects/${projectId}`)

// ── Bulk User Create ───────────────────────────────────────────────────────

export const bulkCreateUsers = (users: BulkUserCreate[]) =>
  apiClient
    .post<BulkUserResult>('/api/admin/users/bulk', { users })
    .then((r) => r.data)
