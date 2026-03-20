// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Copy, Check, ArrowRight } from 'lucide-react'
import { apiClient } from '@/api/client'
import type { ApiKeyCreateResponse } from '@/api/types'

export function Onboarding() {
  const [step, setStep] = useState<'create' | 'show'>('create')
  const [keyName, setKeyName] = useState('Default')
  const [loading, setLoading] = useState(false)
  const [createdKey, setCreatedKey] = useState<ApiKeyCreateResponse | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleCreate() {
    setLoading(true)
    setError('')
    try {
      const { data } = await apiClient.post<ApiKeyCreateResponse>('/api/keys', { name: keyName })
      localStorage.setItem('tb_api_key', data.raw_key)
      setCreatedKey(data)
      setStep('show')
    } catch {
      setError('Could not create API key. Make sure the API server is running.')
    } finally {
      setLoading(false)
    }
  }

  function handleCopy() {
    if (!createdKey) return
    navigator.clipboard.writeText(createdKey.raw_key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-[#6366f1] flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[#e2e8f0]">TokenBudget</h1>
            <p className="text-xs text-[#64748b]">AI Spend Dashboard</p>
          </div>
        </div>

        <div className="bg-[#111118] border border-[#1e1e2e] rounded-2xl p-6">
          {step === 'create' ? (
            <>
              <h2 className="text-base font-semibold text-[#e2e8f0] mb-1">Create your first API key</h2>
              <p className="text-sm text-[#64748b] mb-6">
                This key is used by the SDK to track your AI usage.
              </p>
              <div className="flex flex-col gap-4">
                <div>
                  <label className="block text-xs font-medium text-[#64748b] mb-1.5">Key Name</label>
                  <input
                    className="input"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="e.g. Default, Production"
                    onKeyDown={(e) => e.key === 'Enter' && !loading && handleCreate()}
                    autoFocus
                  />
                </div>
                {error && <p className="text-xs text-red-400">{error}</p>}
                <button
                  className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
                  onClick={handleCreate}
                  disabled={loading || !keyName}
                >
                  {loading ? 'Creating...' : 'Create Key'}
                  {!loading && <ArrowRight size={16} />}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-5 h-5 rounded-full bg-emerald-400/10 flex items-center justify-center">
                  <Check size={12} className="text-emerald-400" />
                </div>
                <h2 className="text-base font-semibold text-[#e2e8f0]">Key created!</h2>
              </div>
              <p className="text-sm text-[#64748b] mb-5">
                Save this key — it won't be shown again.
              </p>
              <div className="flex gap-2 mb-5">
                <input
                  className="input font-mono text-xs flex-1"
                  value={createdKey?.raw_key ?? ''}
                  readOnly
                />
                <button
                  onClick={handleCopy}
                  className="btn-primary flex items-center gap-1.5 flex-shrink-0"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <button
                className="btn-primary w-full flex items-center justify-center gap-2"
                onClick={() => navigate('/dashboard')}
              >
                Go to Dashboard
                <ArrowRight size={16} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
