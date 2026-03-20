// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { DemoBanner } from '@/components/ui/DemoBanner'

export function PageShell() {
  return (
    <div className="flex h-full min-h-screen bg-[#0a0a0f]">
      <Sidebar />
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        <DemoBanner />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
