import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Task, User } from '../api/types'
import TaskCard from '../components/TaskCard'

const ALICE = 1
const BOB = 2
const CAROL = 3

const usersById = new Map<number, User>([
  [ALICE, { id: ALICE, email: 'alice@example.com', full_name: 'Alice' }],
  [BOB, { id: BOB, email: 'bob@example.com', full_name: 'Bob' }],
])

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 10,
    title: 'Write report',
    description: null,
    status: 'todo',
    due_date: '2026-11-20',
    owner_id: ALICE,
    assignee_id: BOB,
    created_at: '2026-11-13T12:00:00Z',
    updated_at: '2026-11-13T12:00:00Z',
    completed_at: null,
    is_overdue: false,
    ...overrides,
  }
}

function renderCard(currentUserId: number, task = makeTask()) {
  const handlers = { onEdit: vi.fn(), onComplete: vi.fn(), onDelete: vi.fn() }
  render(
    <TaskCard
      task={task}
      currentUserId={currentUserId}
      usersById={usersById}
      busy={false}
      {...handlers}
    />,
  )
  return handlers
}

const button = (name: RegExp) => screen.queryByRole('button', { name })

describe('TaskCard permissions (mirror the API rules)', () => {
  it('lets the owner complete, edit and delete', () => {
    renderCard(ALICE)

    expect(button(/complete "write report"/i)).toBeInTheDocument()
    expect(button(/edit "write report"/i)).toBeInTheDocument()
    expect(button(/delete "write report"/i)).toBeInTheDocument()
  })

  it('lets the assignee edit and complete but not delete', () => {
    renderCard(BOB)

    expect(button(/edit/i)).toBeInTheDocument()
    expect(button(/complete/i)).toBeInTheDocument()
    expect(button(/delete/i)).not.toBeInTheDocument()
  })

  it('shows no actions to anyone else', () => {
    renderCard(CAROL)

    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })

  it('hides Complete once the task is done', () => {
    renderCard(ALICE, makeTask({ status: 'done' }))

    expect(button(/complete/i)).not.toBeInTheDocument()
    expect(button(/edit/i)).toBeInTheDocument()
  })
})

it('passes the task to the delete handler', async () => {
  const task = makeTask()
  const { onDelete } = renderCard(ALICE, task)

  await userEvent.click(screen.getByRole('button', { name: /delete/i }))

  expect(onDelete).toHaveBeenCalledWith(task)
})

it('shows names, the overdue badge and a calendar due date', () => {
  renderCard(ALICE, makeTask({ is_overdue: true }))

  expect(screen.getByText('Overdue')).toBeInTheDocument()
  expect(screen.getByText('Bob')).toBeInTheDocument()
  expect(screen.getByText('Alice')).toBeInTheDocument()
  expect(screen.getByText(/20/)).toBeInTheDocument()
})
