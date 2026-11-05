import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconGrid },
  { to: '/upload', label: 'Dataset Upload', roles: ['admin', 'accounts_staff'], icon: IconUpload },
  { to: '/analytics', label: 'Analytics', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconChart },
  { to: '/assistant', label: 'RAG Assistant', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconChat },
  { to: '/anomalies', label: 'Anomaly Detection', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconAlert },
  { to: '/forecast', label: 'Forecasting', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconTrend },
  { to: '/reports', label: 'Reports', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconDoc },
  { to: '/about', label: 'About', roles: ['admin', 'accounts_staff', 'hod', 'principal'], icon: IconInfo },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const [logoutError, setLogoutError] = React.useState('')

  if (!user) return null

  const role = user?.role || ''
  const displayName = user.name || 'Unknown User'
  const initials = displayName
    .split(' ')
    .map((n: string) => n[0])
    .slice(0, 2)
    .join('')

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-ink-700 bg-ink-900/60">
      <div className="flex items-center gap-2.5 border-b border-ink-700 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ledger-500 font-display text-lg font-bold text-ink-950">
          B
        </div>

        <div>
          <p className="font-display text-sm font-semibold leading-none text-parchment">
            BIET FinAssist
          </p>
          <p className="mt-1 text-[11px] leading-none text-parchment/40">
            Financial Command Center
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS
          .filter((item) => item.roles.includes(role))
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'nav-link-active' : ''}`
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}
      </nav>

      <div className="border-t border-ink-700 p-3">
        <div className="mb-2 flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-700 text-xs font-semibold text-ledger-300">
            {initials}
          </div>

          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-parchment">
              {displayName}
            </p>

            <p className="truncate text-[11px] capitalize text-parchment/40">
              {role.replace('_', ' ')}
            </p>
          </div>
        </div>

        {logoutError && (
          <p role="alert" className="mb-2 px-2 text-xs text-risk-mid">{logoutError}</p>
        )}
        <button
          onClick={async () => {
            setLogoutError('')
            try {
              await logout()
            } catch {
              setLogoutError('Your local session ended, but the server could not revoke this token.')
            }
          }}
          className="nav-link w-full justify-start text-parchment/50 hover:text-risk-high"
        >
          <IconLogout className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  )
}

// ---------------- Icons ----------------

function IconGrid(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function IconUpload(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  )
}

function IconChart(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M4 19V9M12 19V4M20 19v-6" />
      <path d="M4 19h16" />
    </svg>
  )
}

function IconChat(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  )
}

function IconAlert(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  )
}

function IconTrend(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="m23 6-9.5 9.5-5-5L1 18" />
      <path d="M17 6h6v6" />
    </svg>
  )
}

function IconDoc(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M14 3v5h5" />
      <path d="M6 3h8l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" />
      <path d="M9 13h6M9 17h6" />
    </svg>
  )
}

function IconInfo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  )
}

function IconLogout(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  )
}