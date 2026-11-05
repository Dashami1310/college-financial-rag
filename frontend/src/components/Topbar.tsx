import React, { useEffect, useState } from 'react'

export default function Topbar({ title }: { title: string }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000 * 30)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="flex items-center justify-between border-b border-ink-700 bg-ink-900/40 px-8 py-4 backdrop-blur-sm">
      <div>
        <h2 className="font-display text-lg font-semibold text-parchment">{title}</h2>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden items-center gap-2 rounded-full border border-ink-600 bg-ink-800/60 px-3 py-1.5 text-xs text-parchment/50 sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ledger-400" />
          Live · {now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
        </div>
      </div>
    </header>
  )
}
