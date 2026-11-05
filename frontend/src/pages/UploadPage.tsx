import React, { useCallback, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader, formatINR } from '../components/UI'
import { DataTable } from '../components/DataTable'
import { uploadApi } from '../api/endpoints'
import { apiErrorMessage } from '../api/client'
import type { UploadResponse } from '../types'

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState('')

  const handleFile = useCallback((f: File) => {
    setError('')
    setResult(null)
    setFile(f)
  }, [])

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0])
  }

  async function submitUpload() {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const res = await uploadApi.upload(file)
      setResult(res.data)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <AppLayout title="Dataset Upload">
      <SectionHeader
        eyebrow="Data Ingestion"
        title="Upload Expenditure Dataset"
        description="Upload a CSV or Excel file with financial year, quarter, department, budget, and expenditure columns."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload dropzone */}
        <div className="lg:col-span-1">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            className={`panel flex flex-col items-center justify-center gap-3 border-2 border-dashed p-8 text-center transition-colors ${
              dragActive ? 'border-ledger-400 bg-ledger-500/5' : 'border-ink-600'
            }`}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink-700 text-ledger-400">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
              </svg>
            </div>
            <p className="text-sm font-medium text-parchment">Drag &amp; drop your file here</p>
            <p className="text-xs text-parchment/40">Supports .csv, .xlsx, .xls</p>
            <label className="btn-secondary cursor-pointer">
              Browse files
              <input
                type="file" accept=".csv,.xlsx,.xls" className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
            </label>
            {file && (
              <div className="mt-2 w-full rounded-lg bg-ink-700/50 px-3 py-2 text-left text-xs text-parchment/70">
                <p className="truncate font-medium">{file.name}</p>
                <p className="text-parchment/40">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            )}
            <button onClick={submitUpload} disabled={!file || uploading} className="btn-primary mt-1 w-full justify-center">
              {uploading ? 'Processing…' : 'Upload & Validate'}
            </button>
            {error && (
              <div className="mt-2 w-full rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-xs text-risk-critical">
                {error}
              </div>
            )}
          </div>

          <div className="panel mt-4 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-parchment/40">Expected Columns</p>
            <ul className="space-y-1 text-xs text-parchment/60">
              {['Financial Year', 'Quarter', 'Department', 'Budget Allocated', 'Actual Expenditure',
                'Remaining Budget (optional)', 'Major Expense Head', 'Number of Transactions',
                'Vendor', 'Approval Status'].map((col) => (
                <li key={col} className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-ledger-400" /> {col}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Preview + summary */}
        <div className="lg:col-span-2">
          {!result ? (
            <div className="panel flex h-full min-h-[300px] items-center justify-center p-8 text-center text-sm text-parchment/40">
              Upload a dataset to see validation results, a data preview, and summary statistics here.
            </div>
          ) : (
            <div className="space-y-4">
              {result.warnings.length > 0 && (
                <div className="rounded-xl border border-risk-mid/30 bg-risk-mid/10 p-4 text-sm text-risk-mid">
                  <p className="mb-1 font-medium">Validation warnings</p>
                  <ul className="list-disc space-y-0.5 pl-4 text-xs">
                    {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  ['Rows Imported', result.summary.row_count],
                  ['Departments', result.summary.departments.length],
                  ['Total Budget', formatINR(result.summary.total_budget_allocated, true)],
                  ['Total Expenditure', formatINR(result.summary.total_actual_expenditure, true)],
                ].map(([label, val]) => (
                  <div key={label as string} className="panel p-4">
                    <p className="text-[11px] uppercase tracking-wide text-parchment/40">{label}</p>
                    <p className="stat-figure mt-1 text-lg font-semibold text-ledger-300">{val}</p>
                  </div>
                ))}
              </div>

              <div className="panel">
                <div className="panel-header">
                  <h3 className="font-display text-sm font-semibold text-parchment">Data Preview</h3>
                  <span className="text-xs text-parchment/40">First 10 rows</span>
                </div>
                <div className="p-4">
                  <DataTable
                    columns={[
                      { key: 'financial_year', label: 'FY' },
                      { key: 'quarter', label: 'Qtr' },
                      { key: 'department', label: 'Department' },
                      { key: 'budget_allocated', label: 'Budget', align: 'right', render: (r) => formatINR(r.budget_allocated) },
                      { key: 'actual_expenditure', label: 'Expenditure', align: 'right', render: (r) => formatINR(r.actual_expenditure) },
                      { key: 'major_expense_head', label: 'Expense Head' },
                    ]}
                    rows={result.preview}
                    keyField="department"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
