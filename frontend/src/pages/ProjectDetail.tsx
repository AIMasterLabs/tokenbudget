// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DollarSign, Activity, Zap, Key, ChevronRight, FolderOpen, AlertCircle, Users, Plus, Trash2 } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { StatCard, Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { SpendOverTime } from '@/components/charts/SpendOverTime'
import { ModelBreakdownChart } from '@/components/charts/ModelBreakdown'
import { getProject, getProjectAnalytics, getProjectTimeseries } from '@/api/projects'
import { getProjectMembers, addProjectMember, removeProjectMember } from '@/api/members'
import { listUsers } from '@/api/admin'
import { useCurrentUser } from '@/contexts/AuthContext'
import { apiClient } from '@/api/client'
import type { ModelBreakdown } from '@/api/types'

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const { isAdmin } = useCurrentUser()
  const queryClient = useQueryClient()
  const [showAddMember, setShowAddMember] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [memberRole, setMemberRole] = useState('viewer')

  const {
    data: project,
    isLoading: projectLoading,
    error: projectError,
  } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  })

  const { data: analytics } = useQuery({
    queryKey: ['project-analytics', id],
    queryFn: () => getProjectAnalytics(id!),
    enabled: !!id,
  })

  const { data: timeseries } = useQuery({
    queryKey: ['project-timeseries', id],
    queryFn: () => getProjectTimeseries(id!),
    enabled: !!id,
  })

  const { data: models } = useQuery({
    queryKey: ['project-models', id],
    queryFn: () =>
      apiClient
        .get<ModelBreakdown[]>(`/api/projects/${id}/analytics/models?period=30d`)
        .then((r) => r.data),
    enabled: !!id,
  })

  // ── Members (admin only) ─────────────────────────────────────────────────
  const { data: members } = useQuery({
    queryKey: ['project-members', id],
    queryFn: () => getProjectMembers(id!),
    enabled: !!id && isAdmin,
  })

  const { data: allUsers } = useQuery({
    queryKey: ['admin-users'],
    queryFn: listUsers,
    enabled: isAdmin && showAddMember,
  })

  const addMemberMutation = useMutation({
    mutationFn: () => addProjectMember(id!, selectedUserId, memberRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', id] })
      setShowAddMember(false)
      setSelectedUserId('')
      setMemberRole('viewer')
    },
  })

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) => removeProjectMember(id!, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', id] })
    },
  })

  // ── Loading ────────────────────────────────────────────────────────────────
  if (projectLoading) {
    return (
      <div className="flex flex-col min-h-full">
        <Header title="Loading..." />
        <div className="p-6">
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <div className="w-8 h-8 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[#64748b]">Loading project...</p>
          </div>
        </div>
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (projectError || !project) {
    return (
      <div className="flex flex-col min-h-full">
        <Header title="Project Not Found" />
        <div className="p-6">
          <Card>
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <AlertCircle size={32} className="text-red-400" />
              <p className="text-sm text-red-400">
                {projectError ? 'Failed to load project. Check that the API is running.' : 'Project not found.'}
              </p>
              <Link
                to="/dashboard/projects"
                className="text-sm text-[#818cf8] hover:text-[#a5b4fc] transition-colors"
              >
                Back to Projects
              </Link>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  // ── Derived values ─────────────────────────────────────────────────────────
  const totalSpend = analytics?.total_cost_usd ?? 0
  const totalRequests = analytics?.total_requests ?? 0
  const avgCost = analytics?.avg_cost_per_request ?? 0
  const color = project.color || '#6366f1'

  return (
    <div className="flex flex-col min-h-full">
      <Header title={project.name} />

      <div className="p-6 flex flex-col gap-6">

        {/* ── Breadcrumb ── */}
        <nav className="flex items-center gap-1.5 text-xs text-[#64748b] animate-fade-in">
          <Link to="/dashboard" className="hover:text-[#c4c4e0] transition-colors">
            Dashboard
          </Link>
          <ChevronRight size={12} className="flex-shrink-0" />
          <Link to="/dashboard/projects" className="hover:text-[#c4c4e0] transition-colors">
            Projects
          </Link>
          <ChevronRight size={12} className="flex-shrink-0" />
          <span className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="text-[#c4c4e0] font-medium">{project.name}</span>
          </span>
        </nav>

        {/* ── Project identity ── */}
        <div className="flex items-center gap-3 animate-fade-in">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{
              background: `linear-gradient(135deg, ${color}30 0%, ${color}10 100%)`,
              border: `1px solid ${color}40`,
            }}
          >
            <FolderOpen size={18} style={{ color }} />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#e2e8f0]">{project.name}</h2>
            {project.description && (
              <p className="text-xs text-[#64748b] mt-0.5">{project.description}</p>
            )}
          </div>
        </div>

        {/* ── Stat Cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            label="Total Spend"
            value={`$${totalSpend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            subValue="Last 30 days"
            icon={<DollarSign size={15} />}
            animationDelay="0ms"
          />
          <StatCard
            label="Requests"
            value={totalRequests.toLocaleString()}
            subValue="Last 30 days"
            icon={<Activity size={15} />}
            animationDelay="60ms"
          />
          <StatCard
            label="Avg Cost / Req"
            value={`$${avgCost.toFixed(4)}`}
            subValue="Per request"
            icon={<Zap size={15} />}
            animationDelay="120ms"
          />
          <StatCard
            label="Active"
            value={project.is_active ? 'Yes' : 'No'}
            subValue="Project status"
            icon={<Key size={15} />}
            animationDelay="180ms"
          />
        </div>

        {/* ── Spend Over Time ── */}
        <div className="animate-slide-up" style={{ animationDelay: '100ms', animationFillMode: 'both' }}>
          <Card title="Spend Over Time" subtitle="Daily spend for the last 30 days">
            {timeseries && timeseries.length > 0 ? (
              <SpendOverTime data={timeseries} />
            ) : (
              <p className="text-sm text-[#64748b] py-8 text-center">No usage data yet.</p>
            )}
          </Card>
        </div>

        {/* ── Model Breakdown ── */}
        <div className="animate-slide-up" style={{ animationDelay: '160ms', animationFillMode: 'both' }}>
          <Card title="Model Breakdown" subtitle="Spend by model">
            {models && models.length > 0 ? (
              <ModelBreakdownChart data={models} />
            ) : (
              <p className="text-sm text-[#64748b] py-8 text-center">No model data yet.</p>
            )}
          </Card>
        </div>

        {/* ── Project Settings ── */}
        <div className="animate-slide-up" style={{ animationDelay: '220ms', animationFillMode: 'both' }}>
          <Card title="Project Settings" subtitle="Project configuration">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <p className="text-xs text-[#64748b]">Slug</p>
                <p className="text-sm font-mono text-[#94a3b8]">{project.slug}</p>
              </div>
              <div className="border-t border-[#1e1e2e] pt-4">
                <p className="text-xs text-[#64748b] mb-3">Project color</p>
                <div className="flex items-center gap-2">
                  <span
                    className="w-5 h-5 rounded-full border-2"
                    style={{
                      backgroundColor: color,
                      borderColor: `${color}80`,
                    }}
                  />
                  <span className="text-xs font-mono text-[#94a3b8]">{color}</span>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ── Members (admin only) ── */}
        {isAdmin && (
          <div className="animate-slide-up" style={{ animationDelay: '280ms', animationFillMode: 'both' }}>
            <Card title="Project Members" subtitle="Manage who has access to this project">
              <div className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users size={16} className="text-[#818cf8]" />
                    <span className="text-xs text-[#64748b]">
                      {members?.length ?? 0} member{members?.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowAddMember(true)}
                    className="btn-primary flex items-center gap-1.5 text-xs px-2.5 py-1.5"
                  >
                    <Plus size={12} />
                    Add Member
                  </button>
                </div>

                {members && members.length > 0 ? (
                  <div className="border-t border-[#1e1e2e] pt-3">
                    {members.map((m) => (
                      <div
                        key={m.user_id}
                        className="flex items-center justify-between py-2 border-b border-[#1e1e2e]/50 last:border-0"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-full bg-[#1a1a24] flex items-center justify-center text-xs text-[#94a3b8] font-medium">
                            {m.user_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm text-[#e2e8f0]">{m.user_name}</p>
                            <p className="text-xs text-[#64748b]">{m.user_email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={m.role === 'admin' ? 'primary' : 'muted'}>{m.role}</Badge>
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
                ) : (
                  <p className="text-xs text-[#64748b] text-center py-4">No members added yet.</p>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Add Member Modal */}
      <Modal open={showAddMember} onClose={() => setShowAddMember(false)} title="Add Project Member">
        <form
          onSubmit={(e) => { e.preventDefault(); addMemberMutation.mutate() }}
          className="flex flex-col gap-3"
        >
          <label className="text-xs text-[#64748b]">User</label>
          <select
            className="input"
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
          >
            <option value="">Select a user...</option>
            {allUsers?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.email})
              </option>
            ))}
          </select>

          <label className="text-xs text-[#64748b]">Role</label>
          <select
            className="input"
            value={memberRole}
            onChange={(e) => setMemberRole(e.target.value)}
          >
            <option value="viewer">Viewer</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowAddMember(false)}
              className="btn-secondary flex-1 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedUserId || addMemberMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {addMemberMutation.isPending ? 'Adding...' : 'Add Member'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
