import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Loading } from './UI'

export function ProtectedRoute({
  children, roles,
}: { children: React.ReactNode; roles?: string[] }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-ink-950">
        <Loading label="Checking your session…" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 bg-ink-950 text-center">
        <p className="font-display text-lg font-semibold text-parchment">Access restricted</p>
        <p className="text-sm text-parchment/50">Your role ({user.role.replace('_', ' ')}) doesn't have permission to view this page.</p>
      </div>
    )
  }

  return <>{children}</>
}
