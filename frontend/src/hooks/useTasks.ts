import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import * as tasksApi from '../api/tasks'
import type { PageRequest } from '../api/tasks'
import type { TaskFilters, TaskInput } from '../api/types'

const TASKS_KEY = ['tasks'] as const

export function useTasks(filters: TaskFilters, page: PageRequest) {
  return useQuery({
    queryKey: [...TASKS_KEY, filters, page],
    queryFn: () => tasksApi.listTasks(filters, page),
    placeholderData: keepPreviousData, // no flicker while paging/filtering
  })
}

/** Every task mutation refreshes all task lists (and notifications, which may change too). */
function useInvalidateTasks() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: TASKS_KEY }),
      queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    ])
}

export function useCreateTask() {
  const invalidate = useInvalidateTasks()
  return useMutation({
    mutationFn: (input: TaskInput) => tasksApi.createTask(input),
    onSuccess: invalidate,
  })
}

export function useUpdateTask() {
  const invalidate = useInvalidateTasks()
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: Partial<TaskInput> }) =>
      tasksApi.updateTask(id, changes),
    onSuccess: invalidate,
  })
}

export function useCompleteTask() {
  const invalidate = useInvalidateTasks()
  return useMutation({ mutationFn: tasksApi.completeTask, onSuccess: invalidate })
}

export function useDeleteTask() {
  const invalidate = useInvalidateTasks()
  return useMutation({ mutationFn: tasksApi.deleteTask, onSuccess: invalidate })
}
