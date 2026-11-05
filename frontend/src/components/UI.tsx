import React from 'react'

// ---------------- Formatting helpers ----------------
export function formatINR(value: number, compact = false): string {
  if (compact) {
    if (Math.abs(value) >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`
    if (Math.abs(value) >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`
    if (Math.abs(value) >= 1e3) return `₹${(value / 1e3).toFixed(1)}K`
  }
  return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

// ---------------- StatCard ----------------
interface StatCardProps {
  label: string
  value: string
  sublabel?: string
  accent?: 'ledger' | 'risk' | 'amber' | 'neutral'
  icon?: React.ReactNode
  trend?: { direction: 'up' | 'down'; value: string } | null
}

const accentMap: Record<string, string> = {
  ledger: 'text-ledger-400',
  risk: 'text-risk-critical',
  amber: 'text-risk-mid',
  neutral: 'text-parchment',
}

export function StatCard({ label, value, sublabel, accent = 'neutral', icon, trend }: StatCardProps) {
  return (
    <div className="panel p-5 animate-tick-in">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-parchment/50">{label}</p>
        {icon && <div className="text-parchment/30">{icon}</div>}
      </div>
      <p className={`stat-figure mt-3 text-3xl font-semibold ${accentMap[accent]}`}>{value}</p>
      <div className="mt-2 flex items-center gap-2">
        {sublabel && <p className="text-xs text-parchment/40">{sublabel}</p>}
        {trend && (
          <span className={`text-xs font-medium ${trend.direction === 'up' ? 'text-ledger-400' : 'text-risk-high'}`}>
            {trend.direction === 'up' ? '▲' : '▼'} {trend.value}
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------- Badge ----------------
export function RiskBadge({ score }: { score: number }) {
  let colorClass = 'bg-ledger-500/15 text-ledger-300'
  let label = 'Low'
  if (score >= 75) {
    colorClass = 'bg-risk-critical/15 text-risk-critical'
    label = 'Critical'
  } else if (score >= 50) {
    colorClass = 'bg-risk-high/15 text-risk-high'
    label = 'High'
  } else if (score >= 25) {
    colorClass = 'bg-risk-mid/15 text-risk-mid'
    label = 'Moderate'
  }
  return (
    <span className={`badge ${colorClass}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label} · {score.toFixed(0)}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    Approved: 'bg-ledger-500/15 text-ledger-300',
    Pending: 'bg-risk-mid/15 text-risk-mid',
    Rejected: 'bg-risk-critical/15 text-risk-critical',
  }
  return <span className={`badge ${map[status] || 'bg-ink-600/50 text-parchment/60'}`}>{status}</span>
}

// ---------------- Loading ----------------
export function Loading({ label = 'Loading data…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-parchment/50">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink-500 border-t-ledger-400" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

// ---------------- EmptyState ----------------
export function EmptyState({
  title, description, action,
}: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink-700 text-ledger-400">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M4 19V5a2 2 0 0 1 2-2h8.5L20 7.5V19a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
          <path d="M14 3v5h5" />
        </svg>
      </div>
      <h3 className="font-display text-base font-semibold text-parchment">{title}</h3>
      <p className="max-w-sm text-sm text-parchment/50">{description}</p>
      {action}
    </div>
  )
}

// ---------------- Section header ----------------
export function SectionHeader({ eyebrow, title, description }: { eyebrow?: string; title: string; description?: string }) {
  return (
    <div className="mb-6">
      {eyebrow && <p className="text-xs font-semibold uppercase tracking-widest text-ledger-400">{eyebrow}</p>}
      <h1 className="mt-1 text-2xl font-semibold text-parchment">{title}</h1>
      {description && <p className="mt-1 text-sm text-parchment/50">{description}</p>}
    </div>
  )
}
