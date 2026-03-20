// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Plus, Trash2, Copy, Check, Key } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Card } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { DataTable } from '@/components/ui/DataTable'
import { EmptyState } from '@/components/ui/EmptyState'
import { useKeys, useCreateKey, useDeleteKey } from '@/hooks/useKeys'
import type { ApiKeyResponse, ApiKeyCreateResponse } from '@/api/types'

export function ApiKeys() {
  const [modalOpen, setModalOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<ApiKeyCreateResponse | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const keys = useKeys()
  const createKey = useCreateKey()
  const deleteKey = useDeleteKey()

  function handleCreate() {
    createKey.mutate(newKeyName, {
      onSuccess: (data) => {
        setCreatedKey(data)
        setNewKeyName('')
      },
    })
  }

  function handleDelete(id: string) {
    deleteKey.mutate(id, {
      onSuccess: () => setDeleteId(null),
    })
  }

  function handleCopy(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleCloseCreate() {
    setModalOpen(false)
    setCreatedKey(null)
    setNewKeyName('')
  }

  const columns = [
    { key: 'name', header: 'Name' },
    { key: 'key_prefix', header: 'Key', render: (row: ApiKeyResponse) => (
      <span className="font-mono text-xs text-[#64748b]">{row.key_prefix}...</span>
    )},
    { key: 'is_active', header: 'Status', render: (row: ApiKeyResponse) => (
      <Badge variant={row.is_active ? 'success' : 'neutral'}>
        {row.is_active ? 'Active' : 'Revoked'}
      </Badge>
    )},
    { key: 'created_at', header: 'Created', render: (row: ApiKeyResponse) => (
      <span className="text-[#64748b] text-xs">{new Date(row.created_at).toLocaleDateString()}</span>
    )},
    { key: 'actions', header: '', render: (row: ApiKeyResponse) => (
      <button
        onClick={() => setDeleteId(row.id)}
        className="text-[#64748b] hover:text-red-400 transition-colors p-1"
        title="Delete key"
      >
        <Trash2 size={14} />
      </button>
    )},
  ]

  return (
    <div className="flex flex-col min-h-full">
      <Header title="API Keys" />

      <div className="p-6 flex flex-col gap-6">
        {/* Actions */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-[#64748b]">
            {keys.data?.length ?? 0} key{keys.data?.length !== 1 ? 's' : ''} total
          </p>
          <button className="btn-primary flex items-center gap-2" onClick={() => setModalOpen(true)}>
            <Plus size={16} />
            Create Key
          </button>
        </div>

        {/* Table */}
        <Card>
          {keys.isLoading ? (
            <div className="text-center text-[#64748b] py-8">Loading...</div>
          ) : !keys.data || keys.data.length === 0 ? (
            <EmptyState
              icon={<Key size={24} />}
              title="No API keys yet"
              description="Create an API key to start tracking your AI usage."
              action={
                <button className="btn-primary flex items-center gap-2" onClick={() => setModalOpen(true)}>
                  <Plus size={16} />
                  Create your first key
                </button>
              }
            />
          ) : (
            <DataTable
              columns={columns as Parameters<typeof DataTable>[0]['columns']}
              data={(keys.data as unknown) as Record<string, unknown>[]}
            />
          )}
        </Card>
      </div>

      {/* Create modal */}
      <Modal open={modalOpen} onClose={handleCloseCreate} title="Create API Key">
        {createdKey ? (
          <div className="flex flex-col gap-4">
            <div className="bg-emerald-400/5 border border-emerald-400/20 rounded-lg p-4">
              <p className="text-xs text-emerald-400 font-medium mb-2">Key created — save it now!</p>
              <p className="text-xs text-[#64748b]">This key will only be shown once. Copy it somewhere safe.</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#64748b] mb-1.5">Your API Key</label>
              <div className="flex gap-2">
                <input
                  className="input font-mono text-xs flex-1"
                  value={createdKey.raw_key}
                  readOnly
                />
                <button
                  onClick={() => handleCopy(createdKey.raw_key)}
                  className="btn-primary flex items-center gap-1.5 flex-shrink-0"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
            <button className="btn-primary w-full" onClick={handleCloseCreate}>
              Done
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-medium text-[#64748b] mb-1.5">Key Name</label>
              <input
                className="input"
                placeholder="e.g. Production, Development"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && newKeyName && handleCreate()}
                autoFocus
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                className="btn-primary flex-1 disabled:opacity-50"
                onClick={handleCreate}
                disabled={!newKeyName || createKey.isPending}
              >
                {createKey.isPending ? 'Creating...' : 'Create Key'}
              </button>
              <button className="btn-ghost" onClick={handleCloseCreate}>Cancel</button>
            </div>
            {createKey.isError && (
              <p className="text-xs text-red-400">Failed to create key. Check your API connection.</p>
            )}
          </div>
        )}
      </Modal>

      {/* Delete modal */}
      <Modal open={deleteId !== null} onClose={() => setDeleteId(null)} title="Delete API Key">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-[#64748b]">
            Deleting this key will immediately revoke access. Any services using it will stop working.
          </p>
          <div className="flex gap-3">
            <button
              className="flex-1 bg-red-500 hover:bg-red-600 text-white font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
              onClick={() => deleteId && handleDelete(deleteId)}
              disabled={deleteKey.isPending}
            >
              {deleteKey.isPending ? 'Deleting...' : 'Delete Key'}
            </button>
            <button className="btn-ghost" onClick={() => setDeleteId(null)}>Cancel</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
