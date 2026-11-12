import { apiFetch } from './client'
import type { User } from './types'

export async function login(email: string, password: string): Promise<string> {
  // OAuth2 password flow expects form fields, with the email in `username`.
  const body = new URLSearchParams({ username: email, password })
  const { access_token } = await apiFetch<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body,
  })
  return access_token
}

export function register(email: string, password: string, fullName: string): Promise<User> {
  return apiFetch<User>('/auth/register', {
    method: 'POST',
    json: { email, password, full_name: fullName },
  })
}

export function fetchMe(): Promise<User> {
  return apiFetch<User>('/users/me')
}
