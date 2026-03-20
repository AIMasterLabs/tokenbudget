// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  BarChart2,
  FolderOpen,
  Target,
  Key,
  Bell,
  Settings,
  Zap,
  LogOut,
  Plug,
  Users,
  UsersRound,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useCurrentUser } from '@/contexts/AuthContext'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true, adminOnly: false },
  { to: '/dashboard/projects', label: 'Projects', icon: FolderOpen, end: false, adminOnly: false },
  { to: '/dashboard/analytics', label: 'Analytics', icon: BarChart2, end: false, adminOnly: false },
  { to: '/dashboard/budgets', label: 'Budgets', icon: Target, end: false, adminOnly: false },
  { to: '/dashboard/alerts', label: 'Alerts', icon: Bell, end: false, adminOnly: false },
  { to: '/dashboard/keys', label: 'API Keys', icon: Key, end: false, adminOnly: false },
  { to: '/dashboard/admin/users', label: 'Users', icon: Users, end: false, adminOnly: true },
  { to: '/dashboard/admin/groups', label: 'Groups', icon: UsersRound, end: false, adminOnly: true },
  { to: '/dashboard/proxy', label: 'Proxy Setup', icon: Plug, end: false, adminOnly: false },
  { to: '/dashboard/settings', label: 'Settings', icon: Settings, end: false, adminOnly: false },
]

export function Sidebar() {
  const { isAdmin, logout } = useCurrentUser()

  function handleLogout() {
    logout()
  }

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 flex flex-col z-40"
      style={{
        background: 'linear-gradient(180deg, #111118 0%, #0e0e16 100%)',
        borderRight: '1px solid #1e1e2e',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[#1e1e2e]">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
            boxShadow: '0 2px 12px rgba(99,102,241,0.4)',
          }}
        >
          <Zap size={15} className="text-white" strokeWidth={2.5} />
        </div>
        <div>
          <span className="text-sm font-bold text-[#e2e8f0] tracking-tight">TokenBudget</span>
          <p className="text-[10px] text-[#64748b] mt-0.5 leading-none">AI Spend Dashboard</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 flex flex-col gap-0.5 overflow-y-auto">
        {navItems.filter((item) => !item.adminOnly || isAdmin).map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium',
                'transition-all duration-150 ease-out group',
                isActive
                  ? 'text-[#c7d2fe] bg-[#6366f1]/10'
                  : 'text-[#64748b] hover:text-[#c4c4e0] hover:bg-[#ffffff06]'
              )
            }
          >
            {({ isActive }) => (
              <>
                {/* Left active border */}
                <span
                  className={clsx(
                    'absolute left-0 top-1/2 -translate-y-1/2 w-0.5 rounded-full',
                    'transition-all duration-200',
                    isActive ? 'h-5 bg-[#6366f1] opacity-100' : 'h-0 opacity-0'
                  )}
                />
                <Icon
                  size={16}
                  className={clsx(
                    'flex-shrink-0 transition-colors duration-150',
                    isActive ? 'text-[#818cf8]' : 'text-[#64748b] group-hover:text-[#9ca3c2]'
                  )}
                />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-[#1e1e2e]">
        <button
          onClick={handleLogout}
          className={clsx(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full',
            'text-[#64748b] hover:text-red-400 hover:bg-red-400/5 border border-transparent',
            'transition-all duration-150 ease-out group'
          )}
        >
          <LogOut size={16} className="flex-shrink-0 transition-colors duration-150 group-hover:text-red-400" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
