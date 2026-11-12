import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiFetch, AUTH_LOGOUT_EVENT, TOKEN_KEY } from '../api/client'

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('apiFetch', () => {
  it('adds the bearer token and the /api/v1 prefix', async () => {
    localStorage.setItem(TOKEN_KEY, 'abc')
    const fetchMock = mockFetch(200, { ok: true })

    await expect(apiFetch('/tasks')).resolves.toEqual({ ok: true })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/tasks')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer abc')
  })

  it('sends JSON bodies with a JSON content type', async () => {
    const fetchMock = mockFetch(201, { id: 1 })

    await apiFetch('/tasks', { method: 'POST', json: { title: 'x' } })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.body).toBe('{"title":"x"}')
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(apiFetch('/tasks/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('throws ApiError carrying the backend detail', async () => {
    mockFetch(422, { detail: 'assignee not found' })

    const error = await apiFetch('/tasks').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, message: 'assignee not found' })
  })

  it('turns FastAPI validation error lists into a readable message', async () => {
    mockFetch(422, { detail: [{ loc: ['body', 'title'], msg: 'Field required' }] })

    await expect(apiFetch('/tasks')).rejects.toMatchObject({ message: 'title: Field required' })
  })

  it('on 401 clears the token and emits the logout event', async () => {
    localStorage.setItem(TOKEN_KEY, 'expired')
    mockFetch(401, { detail: 'invalid or expired token' })
    const listener = vi.fn()
    window.addEventListener(AUTH_LOGOUT_EVENT, listener)

    await expect(apiFetch('/users/me')).rejects.toBeInstanceOf(ApiError)

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(AUTH_LOGOUT_EVENT, listener)
  })
})
