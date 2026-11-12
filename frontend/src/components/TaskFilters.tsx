import { useState } from 'react'

import { TASK_STATUSES } from '../api/types'
import type { TaskFilters as Filters, TaskStatus, User } from '../api/types'

interface Props {
  value: Filters
  users: User[]
  onChange: (next: Filters) => void
}

const fieldClass =
  'mt-1 block w-full min-h-11 rounded-lg border border-slate-300 bg-white px-3 text-sm ' +
  'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none'

/** Removes empty keys so the URL and query keys stay canonical. */
function clean(filters: Filters): Filters {
  return Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== ''),
  ) as Filters
}

export default function TaskFilters({ value, users, onChange }: Props) {
  // An inverted range is kept locally (so the input shows what was typed) but never emitted.
  const [pendingDates, setPendingDates] = useState<Pick<Filters, 'due_after' | 'due_before'> | null>(
    null,
  )
  const dates = pendingDates ?? { due_after: value.due_after, due_before: value.due_before }
  const rangeError =
    pendingDates !== null ? 'The "due after" date must be on or before "due before".' : null

  function changeDate(field: 'due_after' | 'due_before', date: string) {
    const nextDates = { ...dates, [field]: date || undefined }
    if (nextDates.due_after && nextDates.due_before && nextDates.due_after > nextDates.due_before) {
      setPendingDates(nextDates)
      return
    }
    setPendingDates(null)
    onChange(clean({ ...value, ...nextDates }))
  }

  return (
    <section
      aria-label="Filters"
      className="grid grid-cols-1 gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-5"
    >
      <label className="text-sm font-medium text-slate-700">
        Status
        <select
          className={fieldClass}
          value={value.status ?? ''}
          onChange={(e) =>
            onChange(clean({ ...value, status: (e.target.value || undefined) as TaskStatus }))
          }
        >
          <option value="">All</option>
          {TASK_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-medium text-slate-700">
        Assignee
        <select
          className={fieldClass}
          value={value.assignee_id ?? ''}
          onChange={(e) =>
            onChange(
              clean({
                ...value,
                assignee_id: e.target.value ? Number(e.target.value) : undefined,
              }),
            )
          }
        >
          <option value="">Anyone</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-medium text-slate-700">
        Due after
        <input
          type="date"
          className={fieldClass}
          value={dates.due_after ?? ''}
          onChange={(e) => changeDate('due_after', e.target.value)}
        />
      </label>
      <label className="text-sm font-medium text-slate-700">
        Due before
        <input
          type="date"
          className={fieldClass}
          value={dates.due_before ?? ''}
          onChange={(e) => changeDate('due_before', e.target.value)}
        />
      </label>
      <div className="flex items-end">
        <button
          type="button"
          onClick={() => {
            setPendingDates(null)
            onChange({})
          }}
          className="min-h-11 w-full rounded-lg border border-slate-300 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Clear filters
        </button>
      </div>
      {rangeError && (
        <p role="alert" className="text-sm text-red-700 sm:col-span-2 lg:col-span-5">
          {rangeError}
        </p>
      )}
    </section>
  )
}
