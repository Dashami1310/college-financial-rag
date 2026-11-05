import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader } from '../components/UI'
import { FilterSelect } from '../components/DataTable'
import { reportsApi, analyticsApi } from '../api/endpoints'
import { apiErrorMessage } from '../api/client'

const REPORT_TYPES = [
  { value: 'summary', label: 'Financial Summary Report', description: 'Institution-wide KPIs and department breakdown.' },
  { value: 'quarterly', label: 'Quarterly Report', description: 'Expenditure analysis for a specific financial year & quarter.' },
  { value: 'department', label: 'Department Report', description: 'Deep dive into a single department\'s finances.' },
]

export default function ReportsPage() {
  const [filters, setFilters] = useState<{ financial_years: string[]; quarters: string[]; departments: string[] }>({
    financial_years: [], quarters: [], departments: [],
  })
  const [reportType, setReportType] = useState('summary')
  const [fy, setFy] = useState('')
  const [quarter, setQuarter] = useState('')
  const [dept, setDept] = useState('')
  const [format, setFormat] = useState<'pdf' | 'excel'>('pdf')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    analyticsApi.filters().then((res) => setFilters(res.data))
  }, [])

  async function generateReport() {
    setGenerating(true)
    setError('')
    try {
      const res = await reportsApi.generate({
        report_type: reportType,
        financial_year: fy || undefined,
        quarter: quarter || undefined,
        department: dept || undefined,
        export_format: format,
      })
      const blob = new Blob([res.data], {
        type: format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${reportType}_report.${format === 'pdf' ? 'pdf' : 'xlsx'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <AppLayout title="Reports">
      <SectionHeader
        eyebrow="Documentation"
        title="Generate Financial Reports"
        description="Export quarterly, department-level, or institution-wide summary reports as PDF or Excel."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          {REPORT_TYPES.map((rt) => (
            <button
              key={rt.value}
              onClick={() => setReportType(rt.value)}
              className={`panel flex w-full items-start gap-4 p-4 text-left transition-colors ${
                reportType === rt.value ? 'border-ledger-500/60 shadow-glow' : 'hover:border-ink-500'
              }`}
            >
              <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                reportType === rt.value ? 'border-ledger-400 bg-ledger-400' : 'border-ink-500'
              }`}>
                {reportType === rt.value && <span className="h-2 w-2 rounded-full bg-ink-950" />}
              </div>
              <div>
                <p className="font-medium text-parchment">{rt.label}</p>
                <p className="mt-0.5 text-xs text-parchment/50">{rt.description}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="panel h-fit p-5">
          <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-parchment/40">Filters</p>
          <div className="space-y-4">
            <FilterSelect label="Financial Year" value={fy} onChange={setFy} options={filters.financial_years} />
            {reportType === 'quarterly' && (
              <FilterSelect label="Quarter" value={quarter} onChange={setQuarter} options={filters.quarters} />
            )}
            {reportType === 'department' && (
              <FilterSelect label="Department" value={dept} onChange={setDept} options={filters.departments} />
            )}

            <div>
              <label className="mb-1.5 block text-xs font-medium text-parchment/50">Export Format</label>
              <div className="flex gap-2">
                {(['pdf', 'excel'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      format === f ? 'border-ledger-400 bg-ledger-500/10 text-ledger-300' : 'border-ink-500 text-parchment/50 hover:text-parchment'
                    }`}
                  >
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-xs text-risk-critical">
                {error}
              </div>
            )}

            <button onClick={generateReport} disabled={generating} className="btn-primary w-full justify-center">
              {generating ? 'Generating…' : `Download ${format.toUpperCase()}`}
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
