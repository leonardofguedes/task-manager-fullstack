import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import { AuthProvider } from '../auth/AuthContext'
import LoginPage from '../pages/LoginPage'

afterEach(() => {
  vi.unstubAllGlobals()
})

function renderLogin() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

it('shows the backend error when credentials are wrong', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'invalid credentials' }), { status: 401 }),
    ),
  )
  renderLogin()

  await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
  await userEvent.type(screen.getByLabelText(/password/i), 'wrong-pass')
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

  expect(await screen.findByRole('alert')).toHaveTextContent('invalid credentials')
})

it('sends the credentials as an OAuth2 form', async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 't', token_type: 'bearer' })))
    .mockResolvedValue(
      new Response(JSON.stringify({ id: 1, email: 'alice@example.com', full_name: 'Alice' })),
    )
  vi.stubGlobal('fetch', fetchMock)
  renderLogin()

  await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
  await userEvent.type(screen.getByLabelText(/password/i), 'demo1234')
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

  await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/v1/auth/login')
  expect(String(init.body)).toBe('username=alice%40example.com&password=demo1234')
  expect(localStorage.getItem('tm_token')).toBe('t')
})
