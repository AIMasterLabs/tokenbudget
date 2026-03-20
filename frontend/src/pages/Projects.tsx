// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, Plus } from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { useProjects, useCreateProject } from '@/hooks/useProjects'
import type { ProjectCreate } from '@/api/projects'

const PRESET_COLORS = [
  '#3b82f6', // blue
  '#8b5cf6', // purple
  '#10b981', // green
  '#f59e0b', // amber
  '#f43f5e', // red
  '#6366f1', // indigo
]

// Simple 7-point sparkline using random-ish demo values seeded by project id
function Sparkline({ color, seed }: { color: string; seed: string }) {
  const points = Array.from({ length: 7 }, (_, i) => {
    const base = seed.charCodeAt(i % seed.length) % 15
    return base + i * 1.2
  })
  const max = Math.max(...points)
  const min = Math.min(...points)
  const range = max - min || 1
  const w = 50
  const h = 20
  const xs = points.map((_, i) => (i / (points.length - 1)) * w)
  const ys = points.map((v) => h - ((v - min) / range) * (h - 4) - 2)
  const d = xs.map((x, i) => `${i === 0 ? 'M' : 'L'}${x},${ys[i]}`).join(' ')

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} fill="none">
      <polyline
        points={xs.map((x, i) => `${x},${ys[i]}`).join(' ')}
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.8}
        fill="none"
      />
      {/* subtle area fill */}
      <path
        d={`${d} L${w},${h} L0,${h} Z`}
        fill={color}
        opacity={0.08}
      />
    </svg>
  )
}

function ProjectCardSkeleton() {
  return (
    <div className="card-hover animate-fade-in flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Skeleton width={10} height={10} rounded="full" />
        <Skeleton width={120} height={16} />
      </div>
      <Skeleton width="80%" height={12} />
      <div className="flex items-center justify-between pt-1">
        <div className="flex gap-4">
          <Skeleton width={60} height={12} />
          <Skeleton width={50} height={12} />
          <Skeleton width={70} height={12} />
        </div>
        <Skeleton width={50} height={20} />
      </div>
    </div>
  )
}

interface CreateProjectModalProps {
  open: boolean
  onClose: () => void
}

function CreateProjectModal({ open, onClose }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState(PRESET_COLORS[0])
  const createProject = useCreateProject()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    const payload: ProjectCreate = { name: name.trim(), color }
    if (description.trim()) payload.description = description.trim()
    createProject.mutate(payload, {
      onSuccess: () => {
        setName('')
        setDescription('')
        setColor(PRESET_COLORS[0])
        onClose()
      },
    })
  }

  return (
    <Modal open={open} onClose={onClose} title="New Project">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#64748b] uppercase tracking-wider">
            Project Name <span className="text-[#f43f5e]">*</span>
          </label>
          <input
            className="input text-sm"
            placeholder="e.g. Mobile App"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
        </div>

        {/* Description */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-[#64748b] uppercase tracking-wider">
            Description <span className="text-[#3d3d52]">(optional)</span>
          </label>
          <input
            className="input text-sm"
            placeholder="Short description…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Color picker */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold text-[#64748b] uppercase tracking-wider">
            Color
          </label>
          <div className="flex items-center gap-2">
            {PRESET_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className="relative w-7 h-7 rounded-full transition-transform duration-150 flex-shrink-0"
                style={{ backgroundColor: c }}
                title={c}
              >
                {color === c && (
                  <span
                    className="absolute inset-0 rounded-full"
                    style={{ boxShadow: `0 0 0 2px #111118, 0 0 0 4px ${c}` }}
                  />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-ghost text-sm">
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary text-sm"
            disabled={createProject.isPending || !name.trim()}
          >
            {createProject.isPending ? 'Creating…' : 'Create Project'}
          </button>
        </div>

        {createProject.isError && (
          <p className="text-xs text-[#f43f5e] text-center">
            Failed to create project. Please try again.
          </p>
        )}
      </form>
    </Modal>
  )
}

export function Projects() {
  const [modalOpen, setModalOpen] = useState(false)
  const navigate = useNavigate()
  const { data: apiProjects, isLoading } = useProjects()

  const displayProjects = apiProjects ?? []

  return (
    <div className="flex flex-col min-h-full">
      <Header
        title="Projects"
        action={
          <button onClick={() => setModalOpen(true)} className="btn-primary text-xs flex items-center gap-1.5">
            <Plus size={14} />
            New Project
          </button>
        }
      />

      <div className="p-6 flex flex-col gap-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
            <ProjectCardSkeleton />
          </div>
        ) : displayProjects.length === 0 ? (
          <EmptyState
            icon={<FolderOpen size={24} />}
            title="No projects yet"
            description="Create your first project to organize API keys and track spend by team or product."
            action={
              <button onClick={() => setModalOpen(true)} className="btn-primary text-sm flex items-center gap-2">
                <Plus size={15} />
                Create your first project
              </button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {displayProjects.map((project, i) => (
              <div
                key={project.id}
                className="card-hover cursor-pointer animate-slide-up"
                style={{
                  animationDelay: `${i * 60}ms`,
                  animationFillMode: 'both',
                }}
                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/dashboard/projects/${project.id}`)}
              >
                {/* Card header */}
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: project.color }}
                    />
                    <span className="text-sm font-bold text-[#e2e8f0] truncate">
                      {project.name}
                    </span>
                  </div>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
                    style={{
                      background: project.is_active
                        ? 'rgba(16,185,129,0.12)'
                        : 'rgba(100,116,139,0.12)',
                      color: project.is_active ? '#10b981' : '#64748b',
                    }}
                  >
                    {project.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {/* Description */}
                {project.description ? (
                  <p className="text-xs text-[#64748b] mb-4 line-clamp-2 leading-relaxed">
                    {project.description}
                  </p>
                ) : (
                  <p className="text-xs text-[#3d3d52] mb-4 italic">No description</p>
                )}

                {/* Created date + sparkline */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] text-[#64748b]">
                    Created {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex-shrink-0">
                    <Sparkline color={project.color} seed={project.id} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateProjectModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
