// Mirrors the backend Pydantic schemas (see /docs on the API).

export type TaskStatus = 'todo' | 'in_progress' | 'done'

export const TASK_STATUSES: { value: TaskStatus; label: string }[] = [
  { value: 'todo', label: 'To do' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'done', label: 'Done' },
]

export interface User {
  id: number
  email: string
  full_name: string
}

export interface Task {
  id: number
  title: string
  description: string | null
  status: TaskStatus
  due_date: string | null
  owner_id: number
  assignee_id: number | null
  created_at: string
  updated_at: string
  completed_at: string | null
  is_overdue: boolean
}

export interface TaskPage {
  items: Task[]
  total: number
  limit: number
  offset: number
}

export interface TaskInput {
  title: string
  description: string | null
  due_date: string | null
  assignee_id: number | null
  status: TaskStatus
}

export interface TaskFilters {
  status?: TaskStatus
  due_after?: string
  due_before?: string
  assignee_id?: number
}

export interface Notification {
  id: number
  task_id: number
  kind: 'assigned' | 'overdue'
  message: string
  created_at: string
}
