import { apiFetch } from './client'
import type { Task, TaskFilters, TaskInput, TaskPage } from './types'

export interface PageRequest {
  limit: number
  offset: number
}

export function listTasks(filters: TaskFilters, page: PageRequest): Promise<TaskPage> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries({ ...filters, ...page })) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  return apiFetch<TaskPage>(`/tasks?${params}`)
}

export function createTask(input: TaskInput): Promise<Task> {
  return apiFetch<Task>('/tasks', { method: 'POST', json: input })
}

export function updateTask(id: number, changes: Partial<TaskInput>): Promise<Task> {
  return apiFetch<Task>(`/tasks/${id}`, { method: 'PATCH', json: changes })
}

export function completeTask(id: number): Promise<Task> {
  return apiFetch<Task>(`/tasks/${id}/complete`, { method: 'POST' })
}

export function deleteTask(id: number): Promise<void> {
  return apiFetch<void>(`/tasks/${id}`, { method: 'DELETE' })
}
