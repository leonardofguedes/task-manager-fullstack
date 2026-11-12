import { TASK_STATUSES } from '../api/types'
import type { Task, User } from '../api/types'

interface Props {
  task: Task
  currentUserId: number
  usersById: Map<number, User>
  busy: boolean
  onEdit: (task: Task) => void
  onComplete: (task: Task) => void
  onDelete: (task: Task) => void
}

const statusStyle: Record<Task['status'], string> = {
  todo: 'bg-slate-100 text-slate-700',
  in_progress: 'bg-amber-100 text-amber-800',
  done: 'bg-emerald-100 text-emerald-800',
}

function formatDate(isoDate: string): string {
  // Due dates are calendar dates: format them without shifting through the local timezone.
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

const actionClass =
  'min-h-11 rounded-lg px-3 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50'

export default function TaskCard({
  task,
  currentUserId,
  usersById,
  busy,
  onEdit,
  onComplete,
  onDelete,
}: Props) {
  const canEdit = currentUserId === task.owner_id || currentUserId === task.assignee_id
  const canDelete = currentUserId === task.owner_id
  const assignee = task.assignee_id ? usersById.get(task.assignee_id) : undefined
  const owner = usersById.get(task.owner_id)
  const statusLabel = TASK_STATUSES.find((s) => s.value === task.status)?.label

  return (
    <li className="rounded-xl bg-white p-4 ring-1 ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3
          className={`text-base font-semibold break-words ${task.status === 'done' ? 'text-slate-400 line-through' : 'text-slate-900'}`}
        >
          {task.title}
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {task.is_overdue && (
            <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
              Overdue
            </span>
          )}
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusStyle[task.status]}`}
          >
            {statusLabel}
          </span>
        </div>
      </div>

      {task.description && (
        <p className="mt-1 text-sm break-words whitespace-pre-line text-slate-600">
          {task.description}
        </p>
      )}

      <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
        <div>
          <dt className="inline">Due: </dt>
          <dd className="inline font-medium text-slate-700">
            {task.due_date ? formatDate(task.due_date) : '—'}
          </dd>
        </div>
        <div>
          <dt className="inline">Assignee: </dt>
          <dd className="inline font-medium text-slate-700">{assignee?.full_name ?? 'Unassigned'}</dd>
        </div>
        <div>
          <dt className="inline">Owner: </dt>
          <dd className="inline font-medium text-slate-700">{owner?.full_name ?? '—'}</dd>
        </div>
      </dl>

      {(canEdit || canDelete) && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          {canEdit && task.status !== 'done' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onComplete(task)}
              className={`${actionClass} bg-emerald-50 text-emerald-700 hover:bg-emerald-100`}
            >
              Complete
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onEdit(task)}
              className={`${actionClass} bg-slate-100 text-slate-700 hover:bg-slate-200`}
            >
              Edit
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              disabled={busy}
              onClick={() => onDelete(task)}
              className={`${actionClass} text-red-700 hover:bg-red-50`}
            >
              Delete
            </button>
          )}
        </div>
      )}
    </li>
  )
}
