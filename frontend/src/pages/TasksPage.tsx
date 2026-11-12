import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'

import { TASK_STATUSES } from '../api/types'
import type { Task, TaskFilters as Filters, TaskInput, TaskStatus } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { primaryButtonClass } from '../components/AuthCard'
import Layout from '../components/Layout'
import NotificationsPanel from '../components/NotificationsPanel'
import Pagination from '../components/Pagination'
import TaskCard from '../components/TaskCard'
import TaskFilters from '../components/TaskFilters'
import TaskFormDialog from '../components/TaskFormDialog'
import {
  useCompleteTask,
  useCreateTask,
  useDeleteTask,
  useTasks,
  useUpdateTask,
} from '../hooks/useTasks'
import { useUsers } from '../hooks/useUsers'

const PAGE_SIZE = 10
const VALID_STATUSES = new Set<string>(TASK_STATUSES.map((s) => s.value))

/** Filters and page live in the URL: shareable, and they survive a reload. */
function readFilters(params: URLSearchParams): Filters {
  const status = params.get('status')
  const assignee = Number(params.get('assignee_id'))
  return {
    status: status && VALID_STATUSES.has(status) ? (status as TaskStatus) : undefined,
    due_after: params.get('due_after') ?? undefined,
    due_before: params.get('due_before') ?? undefined,
    assignee_id: Number.isInteger(assignee) && assignee > 0 ? assignee : undefined,
  }
}

type DialogState = { mode: 'closed' } | { mode: 'create' } | { mode: 'edit'; task: Task }

export default function TasksPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = useMemo(() => readFilters(searchParams), [searchParams])
  const page = Math.max(1, Number(searchParams.get('page')) || 1)

  const tasks = useTasks(filters, { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const users = useUsers()
  const usersById = useMemo(() => new Map((users.data ?? []).map((u) => [u.id, u])), [users.data])

  const createTask = useCreateTask()
  const updateTask = useUpdateTask()
  const completeTask = useCompleteTask()
  const deleteTask = useDeleteTask()
  const [dialog, setDialog] = useState<DialogState>({ mode: 'closed' })
  const [actionError, setActionError] = useState<string | null>(null)

  function setQuery(next: Filters, nextPage = 1) {
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(next)) {
      if (value !== undefined && value !== '') params.set(key, String(value))
    }
    if (nextPage > 1) params.set('page', String(nextPage))
    setSearchParams(params)
  }

  function closeDialog() {
    createTask.reset()
    updateTask.reset()
    setDialog({ mode: 'closed' })
  }

  function handleSubmit(input: TaskInput) {
    if (dialog.mode === 'edit') {
      updateTask.mutate({ id: dialog.task.id, changes: input }, { onSuccess: closeDialog })
    } else {
      createTask.mutate(input, { onSuccess: closeDialog })
    }
  }

  function runAction(action: Promise<unknown>) {
    setActionError(null)
    action.catch((err: unknown) => setActionError(err instanceof Error ? err.message : 'Failed'))
  }

  if (!user) return null
  const formMutation = dialog.mode === 'edit' ? updateTask : createTask
  const busy = completeTask.isPending || deleteTask.isPending

  return (
    <Layout>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_20rem]">
        <section aria-labelledby="tasks-title" className="min-w-0 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h1 id="tasks-title" className="text-2xl font-bold">
              Tasks
            </h1>
            <button
              type="button"
              className={primaryButtonClass}
              onClick={() => setDialog({ mode: 'create' })}
            >
              New task
            </button>
          </div>

          <TaskFilters value={filters} users={users.data ?? []} onChange={(next) => setQuery(next)} />

          {actionError && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {actionError}
            </p>
          )}
          {tasks.isPending && <p className="text-slate-500">Loading tasks…</p>}
          {tasks.isError && (
            <p role="alert" className="text-red-700">
              Could not load tasks: {tasks.error.message}
            </p>
          )}
          {tasks.data && tasks.data.items.length === 0 && (
            <p className="rounded-xl bg-white p-8 text-center text-slate-500 ring-1 ring-slate-200">
              No tasks match these filters.
            </p>
          )}

          <ul className="space-y-3" aria-busy={tasks.isFetching}>
            {tasks.data?.items.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                currentUserId={user.id}
                usersById={usersById}
                busy={busy}
                onEdit={(t) => setDialog({ mode: 'edit', task: t })}
                onComplete={(t) => runAction(completeTask.mutateAsync(t.id))}
                onDelete={(t) => {
                  if (window.confirm(`Delete "${t.title}"? This cannot be undone.`)) {
                    runAction(deleteTask.mutateAsync(t.id))
                  }
                }}
              />
            ))}
          </ul>

          {tasks.data && tasks.data.total > 0 && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={tasks.data.total}
              onPageChange={(next) => setQuery(filters, next)}
            />
          )}
        </section>

        <NotificationsPanel />
      </div>

      {dialog.mode !== 'closed' && (
        <TaskFormDialog
          key={dialog.mode === 'edit' ? dialog.task.id : 'new'}
          task={dialog.mode === 'edit' ? dialog.task : null}
          users={users.data ?? []}
          submitting={formMutation.isPending}
          error={formMutation.error?.message ?? null}
          onSubmit={handleSubmit}
          onClose={closeDialog}
        />
      )}
    </Layout>
  )
}
