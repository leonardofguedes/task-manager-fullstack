import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import * as authApi from '../api/auth'
import { AUTH_LOGOUT_EVENT, getToken, setToken } from '../api/client'
import type { User } from '../api/types'

interface AuthState {
  user: User | null
  /** True while a stored token is being validated on first load. */
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => getToken() !== null)

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    queryClient.clear()
  }, [queryClient])

  useEffect(() => {
    if (!getToken()) return
    let cancelled = false
    authApi
      .fetchMe()
      .then((me) => !cancelled && setUser(me))
      .catch(() => !cancelled && setUser(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    // apiFetch emits this on any 401 (expired token): drop the session everywhere.
    window.addEventListener(AUTH_LOGOUT_EVENT, logout)
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, logout)
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    setToken(await authApi.login(email, password))
    setUser(await authApi.fetchMe())
  }, [])

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await authApi.register(email, password, fullName)
      await login(email, password)
    },
    [login],
  )

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// oxlint-disable-next-line react/only-export-components -- hook lives next to its provider
export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
