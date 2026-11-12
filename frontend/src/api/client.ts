export const API_BASE = '/api/v1'
export const TOKEN_KEY = 'tm_token'
export const AUTH_LOGOUT_EVENT = 'auth:logout'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ApiRequestInit extends RequestInit {
  json?: unknown
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** fetch wrapper: adds the API prefix, bearer token and JSON handling; throws ApiError. */
export async function apiFetch<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { json, ...rest } = init
  const headers = new Headers(rest.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (json !== undefined) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  })

  if (response.status === 401) {
    setToken(null)
    window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT))
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      // FastAPI validation errors: [{loc: ['body', 'title'], msg: '...'}]
      return body.detail
        .map((e: { loc?: unknown[]; msg?: string }) => {
          const field = e.loc?.filter((part) => part !== 'body' && part !== 'query').join('.')
          return field ? `${field}: ${e.msg}` : String(e.msg)
        })
        .join('; ')
    }
  } catch {
    // Non-JSON error body: fall through to the status text.
  }
  return response.statusText || `Request failed (${response.status})`
}
