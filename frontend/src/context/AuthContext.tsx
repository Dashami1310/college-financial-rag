import React, { createContext, useContext, useEffect, useState } from 'react'
import type { User } from '../types'
import { authApi } from '../api/endpoints'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasRole: (...roles: string[]) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('lgr_token')
    const cachedUser = localStorage.getItem('lgr_user')
    if (token && cachedUser) {
      setUser(JSON.parse(cachedUser))
      // Verify token is still valid in background
      authApi.me().then((res) => {
        setUser(res.data)
        localStorage.setItem('lgr_user', JSON.stringify(res.data))
      }).catch(() => {
        localStorage.removeItem('lgr_token')
        localStorage.removeItem('lgr_user')
        setUser(null)
      }).finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  async function login(email: string, password: string) {
    const res = await authApi.login(email, password)
    localStorage.setItem('lgr_token', res.data.access_token)
    localStorage.setItem('lgr_user', JSON.stringify(res.data.user))
    setUser(res.data.user)
  }

  async function logout() {
    if (localStorage.getItem('lgr_token')) {
      await authApi.logout()
    }
    localStorage.removeItem('lgr_token')
    localStorage.removeItem('lgr_user')
    setUser(null)
  }

  function hasRole(...roles: string[]) {
    return !!user && roles.includes(user.role)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
