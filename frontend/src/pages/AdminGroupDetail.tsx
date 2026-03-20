// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users,
  Plus,
  Trash2,
  AlertCircle,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  X,
} from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import {
  getGroup,
  addMember,
  addMembersBulk,
  removeMember,
  addProjectAccess,
  updateProjectPermissions,
  removeProjectAccess,
} from '@/api/groups'
import { listUsers } from '@/api/admin'
import { getProjects } from '@/api/projects'
import { useCurrentUser } from '@/contexts/AuthContext'
import type { Permission } from '@/api/types'

const ALL_PERMISSIONS: { key: Permission; label: string; description: string }[] = [
  { key: 'view_analytics', label: 'View Analytics', description: 'See charts and summaries' },
  { key: 'view_costs', label: 'View Costs', description: 'See dollar amounts' },
  { key: 'view_users', label: 'View Users', description: 'See per-user breakdown' },
  { key: 'export_reports', label: 'Export Reports', description: 'Download CSV/PDF' },
  { key: 'manage_keys', label: 'Manage Keys', description: 'Create/revoke API keys' },
]

export function AdminGroupDetail() {
  const { id } = useParams<{ id: string }>()
  const { isAdmin, loading: authLoading } = useCurrentUser()
  const queryClient = useQueryClient()

  // UI state
  const [showAddMember, setShowAddMember] = useState(false)
  const [showBulkMembers, setShowBulkMembers] = useState(false)
  const [showAddProject, setShowAddProject] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [bulkUserIds, setBulkUserIds] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [selectedPermissions, setSelectedPermissions] = useState<Permission[]>([])
  const [formError, setFormError] = useState('')

  const groupQuery = useQuery({
    queryKey: ['group', id],
    queryFn: () => getGroup(id!),
    enabled: !!id && isAdmin,
  })

  const usersQuery = useQuery({
    queryKey: ['admin-users'],
    queryFn: listUsers,
    enabled: isAdmin,
  })

  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
    enabled: isAdmin,
  })

  const group = groupQuery.data

  // ── Mutations ──────────────────────────────────────────────────────────

  const addMemberMutation = useMutation({
    mutationFn: () => addMember(id!, selectedUserId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      setShowAddMember(false)
      setSelectedUserId('')
      setFormError('')
    },
    onError: (err: unknown) => {
      setFormError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to add member.',
      )
    },
  })

  const bulkMembersMutation = useMutation({
    mutationFn: (userIds: string[]) => addMembersBulk(id!, userIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      setShowBulkMembers(false)
      setBulkUserIds('')
      setFormError('')
    },
    onError: (err: unknown) => {
      setFormError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to add members.',
      )
    },
  })

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => removeMember(id!, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
    },
  })

  const addProjectMutation = useMutation({
    mutationFn: () => addProjectAccess(id!, selectedProjectId, selectedPermissions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
      setShowAddProject(false)
      setSelectedProjectId('')
      setSelectedPermissions([])
      setFormError('')
    },
    onError: (err: unknown) => {
      setFormError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to add project.',
      )
    },
  })

  const updatePermsMutation = useMutation({
    mutationFn: ({ projectId, perms }: { projectId: string; perms: Permission[] }) =>
      updateProjectPermissions(id!, projectId, perms),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
    },
  })

  const removeProjectMutation = useMutation({
    mutationFn: (projectId: string) => removeProjectAccess(id!, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group', id] })
    },
  })

  // ── Handlers ───────────────────────────────────────────────────────────

  function handleAddMember(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedUserId) {
      setFormError('Select a user.')
      return
    }
    setFormError('')
    addMemberMutation.mutate()
  }

  function handleBulkAdd(e: React.FormEvent) {
    e.preventDefault()
    const ids = bulkUserIds
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (ids.length === 0) {
      setFormError('Enter at least one user ID.')
      return
    }
    setFormError('')
    bulkMembersMutation.mutate(ids)
  }

  function handleAddProject(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedProjectId) {
      setFormError('Select a project.')
      return
    }
    if (selectedPermissions.length === 0) {
      setFormError('Select at least one permission.')
      return
    }
    setFormError('')
    addProjectMutation.mutate()
  }

  function togglePermission(projectId: string, currentPerms: Permission[], perm: Permission) {
    const updated = currentPerms.includes(perm)
      ? currentPerms.filter((p) => p !== perm)
      : [...currentPerms, perm]
    updatePermsMutation.mutate({ projectId, perms: updated })
  }

  function toggleNewPermission(perm: Permission) {
    setSelectedPermissions((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm],
    )
  }

  // ── Guards ─────────────────────────────────────────────────────────────

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/dashboard" replace />

  const existingMemberIds = new Set(group?.members.map((m) => m.user_id) ?? [])
  const existingProjectIds = new Set(group?.projects.map((p) => p.project_id) ?? [])
  const availableUsers = (usersQuery.data ?? []).filter((u) => !existingMemberIds.has(u.id))
  const availableProjects = (projectsQuery.data ?? []).filter(
    (p) => !existingProjectIds.has(p.id),
  )

  return (
    <div className="flex flex-col min-h-full">
      <Header title={group ? group.name : 'Group Detail'} />

      <div className="p-6 flex flex-col gap-6">
        {/* Loading */}
        {groupQuery.isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Error */}
        {groupQuery.error && (
          <Card>
            <div className="flex items-center gap-2 text-red-400 text-sm py-4">
              <AlertCircle size={16} />
              Failed to load group.
            </div>
          </Card>
        )}

        {group && (
          <>
            {/* Group info */}
            <Card>
              <div className="px-5 py-4">
                <h2 className="text-base font-semibold text-[#e2e8f0]">{group.name}</h2>
                {group.description && (
                  <p className="text-sm text-[#64748b] mt-1">{group.description}</p>
                )}
                <div className="flex items-center gap-3 mt-3">
                  <Badge variant="info">
                    {group.member_count} member{group.member_count !== 1 ? 's' : ''}
                  </Badge>
                  <Badge variant="muted">
                    {group.project_count} project{group.project_count !== 1 ? 's' : ''}
                  </Badge>
                  <button
                    onClick={() => setShowHelp(!showHelp)}
                    className="ml-auto text-[#64748b] hover:text-[#818cf8] transition-colors flex items-center gap-1 text-xs"
                  >
                    <HelpCircle size={14} />
                    How Groups Work
                    {showHelp ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>
                </div>
              </div>
            </Card>

            {/* Help panel */}
            {showHelp && (
              <Card>
                <div className="px-5 py-4 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[#e2e8f0]">How Groups Work</h3>
                    <button
                      onClick={() => setShowHelp(false)}
                      className="text-[#64748b] hover:text-[#e2e8f0] transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <ul className="text-xs text-[#94a3b8] flex flex-col gap-2">
                    <li>
                      Users in this group can only see projects assigned below.
                    </li>
                    <li>
                      Permissions control what they see within each project.
                    </li>
                    <li
                      className="px-3 py-2 rounded-lg"
                      style={{
                        background: 'rgba(99,102,241,0.06)',
                        border: '1px solid rgba(99,102,241,0.12)',
                      }}
                    >
                      <strong className="text-[#c7d2fe]">Example:</strong> Engineering group
                      with ProjectA (view_analytics, view_costs) means members see charts and
                      costs but cannot export or manage keys.
                    </li>
                  </ul>
                  <div className="flex flex-col gap-1 mt-1">
                    <span className="text-xs font-medium text-[#64748b]">Available permissions:</span>
                    {ALL_PERMISSIONS.map((p) => (
                      <span key={p.key} className="text-xs text-[#94a3b8]">
                        <code className="text-[#818cf8]">{p.key}</code> — {p.description}
                      </span>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* ── Members Section ─────────────────────────────────────── */}
            <Card>
              <div className="px-5 py-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Users size={16} className="text-[#818cf8]" />
                    <h3 className="text-sm font-semibold text-[#e2e8f0]">Members</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setShowBulkMembers(true)
                        setFormError('')
                      }}
                      className="btn-secondary text-xs px-3 py-1.5"
                    >
                      Add Multiple
                    </button>
                    <button
                      onClick={() => {
                        setShowAddMember(true)
                        setFormError('')
                      }}
                      className="btn-primary flex items-center gap-1 text-xs px-3 py-1.5"
                    >
                      <Plus size={12} />
                      Add Member
                    </button>
                  </div>
                </div>

                {group.members.length === 0 && (
                  <p className="text-sm text-[#64748b] text-center py-6">No members yet.</p>
                )}

                {group.members.length > 0 && (
                  <div className="flex flex-col gap-1">
                    {group.members.map((m) => (
                      <div
                        key={m.user_id}
                        className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-[#ffffff03]"
                      >
                        <div className="flex flex-col">
                          <span className="text-sm text-[#e2e8f0]">{m.name}</span>
                          <span className="text-xs text-[#64748b]">{m.email}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge
                            variant={
                              m.role === 'admin'
                                ? 'primary'
                                : m.role === 'manager'
                                  ? 'default'
                                  : 'muted'
                            }
                          >
                            {m.role}
                          </Badge>
                          <button
                            onClick={() => removeMemberMutation.mutate(m.user_id)}
                            disabled={removeMemberMutation.isPending}
                            className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                            title="Remove member"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* ── Project Access Section ──────────────────────────────── */}
            <Card>
              <div className="px-5 py-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <FolderOpen size={16} className="text-[#818cf8]" />
                    <h3 className="text-sm font-semibold text-[#e2e8f0]">Project Access</h3>
                  </div>
                  <button
                    onClick={() => {
                      setShowAddProject(true)
                      setSelectedPermissions([])
                      setFormError('')
                    }}
                    className="btn-primary flex items-center gap-1 text-xs px-3 py-1.5"
                  >
                    <Plus size={12} />
                    Add Project
                  </button>
                </div>

                {group.projects.length === 0 && (
                  <p className="text-sm text-[#64748b] text-center py-6">
                    No project access configured.
                  </p>
                )}

                {group.projects.length > 0 && (
                  <div className="flex flex-col gap-4">
                    {group.projects.map((pa) => (
                      <div
                        key={pa.project_id}
                        className="border border-[#1e1e2e] rounded-xl p-4"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-sm font-medium text-[#e2e8f0]">
                            {pa.project_name}
                          </span>
                          <button
                            onClick={() => removeProjectMutation.mutate(pa.project_id)}
                            disabled={removeProjectMutation.isPending}
                            className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                            title="Remove project access"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {ALL_PERMISSIONS.map((p) => (
                            <label
                              key={p.key}
                              className="flex items-center gap-1.5 text-xs cursor-pointer select-none"
                            >
                              <input
                                type="checkbox"
                                checked={pa.permissions.includes(p.key)}
                                onChange={() =>
                                  togglePermission(pa.project_id, pa.permissions, p.key)
                                }
                                className="accent-[#6366f1] w-3.5 h-3.5"
                              />
                              <span
                                className={
                                  pa.permissions.includes(p.key)
                                    ? 'text-[#c7d2fe]'
                                    : 'text-[#64748b]'
                                }
                              >
                                {p.label}
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </>
        )}
      </div>

      {/* ── Add Member Modal ─────────────────────────────────────────── */}
      <Modal
        open={showAddMember}
        onClose={() => {
          setShowAddMember(false)
          setFormError('')
        }}
        title="Add Member"
      >
        <form onSubmit={handleAddMember} className="flex flex-col gap-3">
          <select
            className="input"
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
          >
            <option value="">Select a user...</option>
            {availableUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.email})
              </option>
            ))}
          </select>

          {formError && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400"
              style={{
                background: 'rgba(244,63,94,0.08)',
                border: '1px solid rgba(244,63,94,0.15)',
              }}
            >
              {formError}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setShowAddMember(false)
                setFormError('')
              }}
              className="btn-secondary flex-1 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addMemberMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {addMemberMutation.isPending ? 'Adding...' : 'Add Member'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Bulk Add Members Modal ───────────────────────────────────── */}
      <Modal
        open={showBulkMembers}
        onClose={() => {
          setShowBulkMembers(false)
          setFormError('')
        }}
        title="Add Multiple Members"
      >
        <form onSubmit={handleBulkAdd} className="flex flex-col gap-3">
          <p className="text-xs text-[#64748b]">
            Paste user IDs below, one per line or comma-separated.
          </p>
          <textarea
            className="input min-h-[120px] resize-none font-mono text-xs"
            placeholder={"user-id-1\nuser-id-2\nuser-id-3"}
            value={bulkUserIds}
            onChange={(e) => setBulkUserIds(e.target.value)}
            autoFocus
          />

          {formError && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400"
              style={{
                background: 'rgba(244,63,94,0.08)',
                border: '1px solid rgba(244,63,94,0.15)',
              }}
            >
              {formError}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setShowBulkMembers(false)
                setFormError('')
              }}
              className="btn-secondary flex-1 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={bulkMembersMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {bulkMembersMutation.isPending ? 'Adding...' : 'Add Members'}
            </button>
          </div>
        </form>
      </Modal>

      {/* ── Add Project Modal ────────────────────────────────────────── */}
      <Modal
        open={showAddProject}
        onClose={() => {
          setShowAddProject(false)
          setFormError('')
        }}
        title="Add Project Access"
      >
        <form onSubmit={handleAddProject} className="flex flex-col gap-3">
          <select
            className="input"
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
          >
            <option value="">Select a project...</option>
            {availableProjects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium text-[#94a3b8]">Permissions</span>
            {ALL_PERMISSIONS.map((p) => (
              <label
                key={p.key}
                className="flex items-center gap-2 text-xs cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  checked={selectedPermissions.includes(p.key)}
                  onChange={() => toggleNewPermission(p.key)}
                  className="accent-[#6366f1] w-3.5 h-3.5"
                />
                <span className="text-[#e2e8f0]">{p.label}</span>
                <span className="text-[#64748b]">— {p.description}</span>
              </label>
            ))}
          </div>

          {formError && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400"
              style={{
                background: 'rgba(244,63,94,0.08)',
                border: '1px solid rgba(244,63,94,0.15)',
              }}
            >
              {formError}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setShowAddProject(false)
                setFormError('')
              }}
              className="btn-secondary flex-1 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addProjectMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {addProjectMutation.isPending ? 'Adding...' : 'Add Project'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
