import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'

import TaskFilters from '../components/TaskFilters'

const users = [
  { id: 1, email: 'alice@example.com', full_name: 'Alice' },
  { id: 2, email: 'bob@example.com', full_name: 'Bob' },
]

it('emits the selected status', async () => {
  const onChange = vi.fn()
  render(<TaskFilters value={{}} users={users} onChange={onChange} />)

  await userEvent.selectOptions(screen.getByLabelText(/status/i), 'done')

  expect(onChange).toHaveBeenCalledWith({ status: 'done' })
})

it('emits the selected assignee as a number', async () => {
  const onChange = vi.fn()
  render(<TaskFilters value={{ status: 'todo' }} users={users} onChange={onChange} />)

  await userEvent.selectOptions(screen.getByLabelText(/assignee/i), 'Bob')

  expect(onChange).toHaveBeenCalledWith({ status: 'todo', assignee_id: 2 })
})

it('emits a valid due date range', () => {
  const onChange = vi.fn()
  render(<TaskFilters value={{ due_after: '2026-11-10' }} users={users} onChange={onChange} />)

  fireEvent.change(screen.getByLabelText(/due before/i), { target: { value: '2026-11-20' } })

  expect(onChange).toHaveBeenCalledWith({ due_after: '2026-11-10', due_before: '2026-11-20' })
})

it('shows an error for an inverted range and does not emit it', () => {
  const onChange = vi.fn()
  render(<TaskFilters value={{ due_after: '2026-11-20' }} users={users} onChange={onChange} />)

  fireEvent.change(screen.getByLabelText(/due before/i), { target: { value: '2026-11-10' } })

  expect(screen.getByRole('alert')).toHaveTextContent(/after/i)
  expect(onChange).not.toHaveBeenCalled()
})

it('clears every filter', async () => {
  const onChange = vi.fn()
  render(<TaskFilters value={{ status: 'done', due_after: '2026-11-01' }} users={users} onChange={onChange} />)

  await userEvent.click(screen.getByRole('button', { name: /clear/i }))

  expect(onChange).toHaveBeenCalledWith({})
})
