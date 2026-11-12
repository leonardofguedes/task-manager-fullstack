import { apiFetch } from './client'
import type { Notification } from './types'

export function listNotifications(limit = 20): Promise<Notification[]> {
  return apiFetch<Notification[]>(`/notifications?limit=${limit}`)
}
