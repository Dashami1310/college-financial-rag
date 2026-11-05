import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiErrorMessage } from '../api/client'

const DEMO_ACCOUNTS = [
  { role: 'Admin', email: 'admin@college.edu', password: 'Admin@123' },
  { role: 'Accounts Staff', email: 'accounts@college.edu', password: 'Accounts@123' },
  { role: 'HOD (AIML)', email: 'hod.aiml@college.edu', password: 'Hod@123' },
  { role: 'Principal', email: 'principal@college.edu', password: 'Principal@123' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-ink-950">
      {/* Left: brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-ink-900 p-12 lg:flex">
        <div className="absolute inset-0 bg-grid-fade" />
        <div className="absolute -left-24 top-1/3 h-64 w-64 rounded-full bg-ledger-500/10 blur-3xl" />
        <div className="relative z-10 flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-ledger-500 font-display text-xl font-bold text-ink-950">L</div>
          <p className="font-display text-lg font-semibold text-parchment">BIET FinAssist</p>
        </div>

        <div className="relative z-10 max-w-md">
          <p className="text-xs font-semibold uppercase tracking-widest text-ledger-400">Major Project · AI &amp; ML</p>
          <h1 className="mt-3 font-display text-4xl font-semibold leading-tight text-parchment">
            RAG-Based College Financial Expenditure Analytics &amp; Anomaly Detection
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-parchment/50">
            Retrieval-Augmented Generation, Isolation Forest anomaly detection, and time-series
            forecasting — unified into one live financial command center for technical institutions.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-ink-700 pt-6">
            {[['12', 'Departments'], ['FAISS', 'Vector Store'], ['Gemini', 'RAG Engine']].map(([v, l]) => (
              <div key={l}>
                <p className="font-mono text-xl font-semibold text-ledger-300">{v}</p>
                <p className="text-[11px] text-parchment/40">{l}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-[11px] text-parchment/30">
          Dept. of AI &amp; ML · Bapuji Institute of Engineering and Technology, Davangere
        </p>
      </div>

      {/* Right: login form */}
      <div className="flex w-full flex-col items-center justify-center px-6 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-ledger-500 font-display text-lg font-bold text-ink-950">L</div>
              <p className="font-display text-base font-semibold text-parchment">BIET FinAssist</p>
            </div>
          </div>

          <h2 className="font-display text-2xl font-semibold text-parchment">Sign in</h2>
          <p className="mt-1 text-sm text-parchment/50">Access your institution's financial command center.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-parchment/60">Email address</label>
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="input-field" placeholder="you@college.edu"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-parchment/60">Password</label>
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="input-field" placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-sm text-risk-critical">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-8 rounded-xl border border-ink-600/60 bg-ink-800/40 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-parchment/40">Demo Accounts (RBAC)</p>
            <div className="space-y-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => { setEmail(acc.email); setPassword(acc.password) }}
                  className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs hover:bg-ink-700/50 transition-colors"
                >
                  <span className="font-medium text-parchment/70">{acc.role}</span>
                  <span className="font-mono text-parchment/40">{acc.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
