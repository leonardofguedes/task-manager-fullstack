import { useQuery } from '@tanstack/react-query'

import { listNotifications } from '../api/notifications'

export const NOTIFICATIONS_POLL_MS = 30_000

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications(),
    refetchInterval: NOTIFICATIONS_POLL_MS,
  })
}
