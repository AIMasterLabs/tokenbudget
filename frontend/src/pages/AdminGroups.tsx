// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Navigate } from 'react-router-dom'
import { Users, Plus, FolderOpen, AlertCircle } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { listGroups, createGroup } from '@/api/groups'
import { useCurrentUser } from '@/contexts/AuthContext'

export function AdminGroups() {
  const { isAdmin, loading: authLoading } = useCurrentUser()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [formError, setFormError] = useState('')

  const { data: groups, isLoading, error } = useQuery({
    queryKey: ['groups'],
    queryFn: listGroups,
    enabled: isAdmin,
  })

  const createMutation = useMutation({
    mutationFn: () => createGroup(newName.trim(), newDesc.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      resetForm()
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to create group.'
      setFormError(msg)
    },
  })

  function resetForm() {
    setShowCreateModal(false)
    setNewName('')
    setNewDesc('')
    setFormError('')
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) {
      setFormError('Group name is required.')
      return
    }
    setFormError('')
    createMutation.mutate()
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/dashboard" replace />

  return (
    <div className="flex flex-col min-h-full">
      <Header title="User Groups" />

      <div className="p-6 flex flex-col gap-6">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-[#818cf8]" />
            <h2 className="text-sm font-semibold text-[#e2e8f0]">All Groups</h2>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2 text-xs px-3 py-2"
          >
            <Plus size={14} />
            Create Group
          </button>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#6366f1] border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {/* Error */}
        {error && (
          <Card>
            <div className="flex items-center gap-2 text-red-400 text-sm py-4">
              <AlertCircle size={16} />
              Failed to load groups.
            </div>
          </Card>
        )}

        {/* Groups list */}
        {groups && groups.length > 0 && (
          <div className="grid gap-3">
            {groups.map((g) => (
              <Card key={g.id}>
                <button
                  onClick={() => navigate(`/dashboard/admin/groups/${g.id}`)}
                  className="w-full text-left px-5 py-4 flex items-center justify-between hover:bg-[#ffffff03] transition-colors rounded-xl"
                >
                  <div className="flex flex-col gap-1">
                    <span className="text-sm font-semibold text-[#e2e8f0]">{g.name}</span>
                    {g.description && (
                      <span className="text-xs text-[#64748b]">{g.description}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="info">
                      <Users size={10} className="mr-1" />
                      {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                    </Badge>
                    <Badge variant="muted">
                      <FolderOpen size={10} className="mr-1" />
                      {g.project_count} project{g.project_count !== 1 ? 's' : ''}
                    </Badge>
                  </div>
                </button>
              </Card>
            ))}
          </div>
        )}

        {groups && groups.length === 0 && (
          <Card>
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <Users size={32} className="text-[#64748b]" />
              <p className="text-sm text-[#64748b]">No groups yet. Create one to get started.</p>
            </div>
          </Card>
        )}
      </div>

      {/* Create Group Modal */}
      <Modal open={showCreateModal} onClose={resetForm} title="Create Group">
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <input
            type="text"
            className="input"
            placeholder="Group name (e.g. Engineering)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
          />
          <textarea
            className="input min-h-[80px] resize-none"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
          />

          {formError && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400"
              style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.15)' }}
            >
              {formError}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={resetForm} className="btn-secondary flex-1 text-sm">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Group'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
