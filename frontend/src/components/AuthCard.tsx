import type { ReactNode } from 'react'

export default function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <p className="text-sm font-semibold tracking-wide text-indigo-600 uppercase">
          Task Manager
        </p>
        <h1 className="mt-1 mb-6 text-2xl font-bold text-slate-900">{title}</h1>
        {children}
      </div>
    </main>
  )
}

export const inputClass =
  'mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-slate-900 ' +
  'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none'

export const primaryButtonClass =
  'inline-flex min-h-11 items-center justify-center rounded-lg bg-indigo-600 px-4 font-semibold ' +
  'text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60'
