import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { TASK_STATUSES } from '../api/types'
import type { Task, TaskInput, TaskStatus, User } from '../api/types'
import { inputClass, primaryButtonClass } from './AuthCard'

interface Props {
  task: Task | null // null = create
  users: User[]
  submitting: boolean
  error: string | null
  onSubmit: (input: TaskInput) => void
  onClose: () => void
}

export default function TaskFormDialog({ task, users, submitting, error, onSubmit, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [dueDate, setDueDate] = useState(task?.due_date ?? '')
  const [assigneeId, setAssigneeId] = useState(task?.assignee_id ? String(task.assignee_id) : '')
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? 'todo')

  useEffect(() => {
    // Native <dialog>: focus trap, Esc to close and backdrop come for free.
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
  }, [])

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit({
      title: title.trim(),
      description: description.trim() || null,
      due_date: dueDate || null,
      assignee_id: assigneeId ? Number(assigneeId) : null,
      status,
    })
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      aria-labelledby="task-dialog-title"
      className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl p-0 shadow-xl backdrop:bg-slate-900/40"
    >
      <form onSubmit={handleSubmit} className="space-y-4 p-6">
        <h2 id="task-dialog-title" className="text-xl font-bold text-slate-900">
          {task ? 'Edit task' : 'New task'}
        </h2>
        <label className="block text-sm font-medium text-slate-700">
          Title
          <input
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={inputClass}
            autoFocus
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Description
          <textarea
            maxLength={2000}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputClass}
          />
        </label>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block text-sm font-medium text-slate-700">
            Due date
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className={inputClass}
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Status
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as TaskStatus)}
              className={inputClass}
            >
              {TASK_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Assignee
            <select
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
              className={inputClass}
            >
              <option value="">Unassigned</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            className="min-h-11 rounded-lg px-4 font-medium text-slate-700 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button type="submit" disabled={submitting} className={primaryButtonClass}>
            {submitting ? 'Saving…' : task ? 'Save changes' : 'Create task'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
