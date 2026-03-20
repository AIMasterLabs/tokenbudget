// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Plus, Trash2, AlertCircle, Shield, User, Upload, HelpCircle } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { listUsers, createUser, deactivateUser } from '@/api/admin'
import { bulkCreateUsers } from '@/api/groups'
import { useCurrentUser } from '@/contexts/AuthContext'
import { Navigate } from 'react-router-dom'
import type { BulkUserCreate, BulkUserResult } from '@/api/types'

export function AdminUsers() {
  const { isAdmin, loading: authLoading } = useCurrentUser()
  const queryClient = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newName, setNewName] = useState('')
  const [newRole, setNewRole] = useState('viewer')
  const [newDept, setNewDept] = useState('')
  const [formError, setFormError] = useState('')

  // Bulk add state
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [bulkJson, setBulkJson] = useState('')
  const [bulkError, setBulkError] = useState('')
  const [bulkResult, setBulkResult] = useState<BulkUserResult | null>(null)

  // Role help tooltip
  const [showRoleHelp, setShowRoleHelp] = useState(false)

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['admin-users'],
    queryFn: listUsers,
    enabled: isAdmin,
  })

  const addMutation = useMutation({
    mutationFn: () => createUser(newEmail, newPassword, newName, newRole, newDept || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      resetForm()
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to create user.'
      setFormError(msg)
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (uid: string) => deactivateUser(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const bulkMutation = useMutation({
    mutationFn: (payload: BulkUserCreate[]) => bulkCreateUsers(payload),
    onSuccess: (result) => {
      setBulkResult(result)
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
    onError: (err: unknown) => {
      setBulkError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Bulk creation failed.',
      )
    },
  })

  function resetForm() {
    setShowAddModal(false)
    setNewEmail('')
    setNewPassword('')
    setNewName('')
    setNewRole('viewer')
    setNewDept('')
    setFormError('')
  }

  function resetBulk() {
    setShowBulkModal(false)
    setBulkJson('')
    setBulkError('')
    setBulkResult(null)
  }

  function handleBulkSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBulkError('')
    setBulkResult(null)
    try {
      const parsed = JSON.parse(bulkJson)
      if (!Array.isArray(parsed) || parsed.length === 0) {
        setBulkError('JSON must be a non-empty array of user objects.')
        return
      }
      bulkMutation.mutate(parsed)
    } catch {
      setBulkError('Invalid JSON. Please check your input.')
    }
  }

  function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!newEmail.trim() || !newPassword.trim() || !newName.trim()) {
      setFormError('All fields are required.')
      return
    }
    setFormError('')
    addMutation.mutate()
  }

  if (authLoading) return null
  if (!isAdmin) return <Navigate to="/dashboard" replace />

  return (
    <div className="flex flex-col min-h-full">
      <Header title="User Management" />

      <div className="p-6 flex flex-col gap-6">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-[#818cf8]" />
            <h2 className="text-sm font-semibold text-[#e2e8f0]">All Users</h2>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                onClick={() => setShowRoleHelp(!showRoleHelp)}
                className="text-[#64748b] hover:text-[#818cf8] transition-colors p-1"
                title="Roles & groups help"
              >
                <HelpCircle size={16} />
              </button>
              {showRoleHelp && (
                <div
                  className="absolute right-0 top-8 w-64 z-50 rounded-xl p-4 text-xs text-[#94a3b8] flex flex-col gap-2 shadow-2xl"
                  style={{
                    background: '#111118',
                    border: '1px solid #1e1e2e',
                  }}
                >
                  <strong className="text-[#e2e8f0]">Roles</strong>
                  <p><code className="text-[#818cf8]">admin</code> — full access to everything</p>
                  <p><code className="text-[#818cf8]">manager</code> — can manage projects and users</p>
                  <p><code className="text-[#818cf8]">viewer</code> — read-only access</p>
                  <strong className="text-[#e2e8f0] mt-1">Groups</strong>
                  <p>Groups control which projects a user can access and what they can do within each project.</p>
                </div>
              )}
            </div>
            <button
              onClick={() => setShowBulkModal(true)}
              className="btn-secondary flex items-center gap-2 text-xs px-3 py-2"
            >
              <Upload size={14} />
              Bulk Add Users
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary flex items-center gap-2 text-xs px-3 py-2"
            >
              <Plus size={14} />
              Add User
            </button>
          </div>
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
              Failed to load users.
            </div>
          </Card>
        )}

        {/* Table */}
        {users && users.length > 0 && (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-[#64748b] border-b border-[#1e1e2e]">
                    <th className="text-left font-medium py-3 px-4">Name</th>
                    <th className="text-left font-medium py-3 px-4">Email</th>
                    <th className="text-left font-medium py-3 px-4">Role</th>
                    <th className="text-left font-medium py-3 px-4">Groups</th>
                    <th className="text-left font-medium py-3 px-4">Department</th>
                    <th className="text-left font-medium py-3 px-4">Status</th>
                    <th className="text-right font-medium py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-[#1e1e2e]/50 last:border-0 hover:bg-[#ffffff03]">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {u.role === 'admin' ? (
                            <Shield size={14} className="text-[#818cf8] flex-shrink-0" />
                          ) : (
                            <User size={14} className="text-[#64748b] flex-shrink-0" />
                          )}
                          <span className="text-sm text-[#e2e8f0]">{u.name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-[#94a3b8]">{u.email}</td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={u.role === 'admin' ? 'primary' : u.role === 'manager' ? 'default' : 'muted'}
                        >
                          {u.role}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {u.groups && u.groups.length > 0 ? (
                            u.groups.map((gName) => (
                              <Badge key={gName} variant="info">
                                {gName}
                              </Badge>
                            ))
                          ) : (
                            <span className="text-xs text-[#64748b]">-</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-[#94a3b8]">{u.department || '-'}</td>
                      <td className="py-3 px-4">
                        <Badge variant={u.is_active !== false ? 'success' : 'danger'}>
                          {u.is_active !== false ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {u.is_active !== false && u.role !== 'admin' && (
                          <button
                            onClick={() => deactivateMutation.mutate(u.id)}
                            disabled={deactivateMutation.isPending}
                            className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                            title="Deactivate user"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {users && users.length === 0 && (
          <Card>
            <div className="flex flex-col items-center justify-center py-12 gap-2">
              <Users size={32} className="text-[#64748b]" />
              <p className="text-sm text-[#64748b]">No users found.</p>
            </div>
          </Card>
        )}
      </div>

      {/* Add User Modal */}
      <Modal open={showAddModal} onClose={resetForm} title="Add User">
        <form onSubmit={handleAdd} className="flex flex-col gap-3">
          <input
            type="text"
            className="input"
            placeholder="Full name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            autoFocus
          />
          <input
            type="email"
            className="input"
            placeholder="Email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
          />
          <input
            type="password"
            className="input"
            placeholder="Password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <select
            className="input"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
          >
            <option value="viewer">Viewer</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
          <input
            type="text"
            className="input"
            placeholder="Department (optional)"
            value={newDept}
            onChange={(e) => setNewDept(e.target.value)}
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
              disabled={addMutation.isPending}
              className="btn-primary flex-1 text-sm"
            >
              {addMutation.isPending ? 'Creating...' : 'Create User'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Bulk Add Users Modal */}
      <Modal open={showBulkModal} onClose={resetBulk} title="Bulk Add Users" className="max-w-lg">
        <form onSubmit={handleBulkSubmit} className="flex flex-col gap-3">
          <p className="text-xs text-[#64748b]">
            Paste a JSON array of users below. Each user needs email, password, name, role, and groups.
          </p>
          <textarea
            className="input min-h-[180px] resize-none font-mono text-xs"
            placeholder={`[
  { "email": "alice@company.com", "password": "temp123", "name": "Alice", "role": "member", "groups": ["Engineering"] },
  { "email": "bob@company.com", "password": "temp456", "name": "Bob", "role": "viewer", "groups": ["Marketing"] }
]`}
            value={bulkJson}
            onChange={(e) => setBulkJson(e.target.value)}
            autoFocus
          />

          {bulkError && (
            <div
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-red-400"
              style={{ background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.15)' }}
            >
              {bulkError}
            </div>
          )}

          {bulkResult && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-3">
                <Badge variant="success">{bulkResult.created} created</Badge>
                {bulkResult.failed > 0 && (
                  <Badge variant="danger">{bulkResult.failed} failed</Badge>
                )}
              </div>
              {bulkResult.results.filter((r) => !r.success).length > 0 && (
                <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                  {bulkResult.results
                    .filter((r) => !r.success)
                    .map((r) => (
                      <div key={r.email} className="text-xs text-red-400">
                        {r.email}: {r.error}
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={resetBulk} className="btn-secondary flex-1 text-sm">
              {bulkResult ? 'Close' : 'Cancel'}
            </button>
            {!bulkResult && (
              <button
                type="submit"
                disabled={bulkMutation.isPending}
                className="btn-primary flex-1 text-sm"
              >
                {bulkMutation.isPending ? 'Adding...' : 'Add Users'}
              </button>
            )}
          </div>
        </form>
      </Modal>
    </div>
  )
}
