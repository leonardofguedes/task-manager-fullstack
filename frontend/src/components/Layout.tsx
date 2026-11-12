import type { ReactNode } from 'react'

import { useAuth } from '../auth/AuthContext'

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <span className="text-lg font-bold text-indigo-600">Task Manager</span>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-slate-600 sm:inline">{user?.full_name}</span>
            <button
              type="button"
              onClick={logout}
              className="min-h-11 rounded-lg px-3 font-medium text-slate-700 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  )
}
