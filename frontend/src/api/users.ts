import { apiFetch } from './client'
import type { User } from './types'

export function fetchUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users')
}
