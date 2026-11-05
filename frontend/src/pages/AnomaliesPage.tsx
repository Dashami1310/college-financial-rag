import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader, Loading, StatCard, RiskBadge, formatINR } from '../components/UI'
import { DataTable } from '../components/DataTable'
import { anomalyApi } from '../api/endpoints'
import { apiErrorMessage } from '../api/client'
import type { AnomalyDetectionResponse } from '../types'
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ZAxis, Cell,
} from 'recharts'

export default function AnomaliesPage() {
  const [data, setData] = useState<AnomalyDetectionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  function runDetection() {
    setLoading(true)
    setError('')
    anomalyApi.detect()
      .then((res) => setData(res.data))
      .catch((err) => setError(apiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => { runDetection() }, [])

  const scatterData = data?.results.map((r) => ({
    x: r.risk_score,
    y: r.anomaly_score,
    z: r.is_anomaly ? 80 : 30,
    department: r.department,
    isAnomaly: r.is_anomaly,
  })) ?? []

  return (
    <AppLayout title="Anomaly Detection">
      <SectionHeader
        eyebrow="Machine Learning · Isolation Forest"
        title="Financial Anomaly Detection"
        description="Unsupervised ML flags overspending, unusual expenditure, budget violations, and high-risk departments."
      />

      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-parchment/50">
          {data ? `${data.total_records_analyzed} records analyzed` : ''}
        </p>
        <button onClick={runDetection} disabled={loading} className="btn-secondary">
          {loading ? 'Analyzing…' : 'Re-run Detection'}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-risk-critical/30 bg-risk-critical/10 px-3 py-2 text-sm text-risk-critical">
          {error}
        </div>
      )}

      {loading ? (
        <Loading label="Running Isolation Forest…" />
      ) : !data || data.total_records_analyzed === 0 ? (
        <div className="panel p-12 text-center text-sm text-parchment/40">
          No data available. Upload a dataset first to run anomaly detection.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Records Analyzed" value={String(data.total_records_analyzed)} accent="neutral" />
            <StatCard label="Anomalies Found" value={String(data.anomalies_found)} accent="amber" sublabel={`${((data.anomalies_found / data.total_records_analyzed) * 100).toFixed(1)}% of records`} />
            <StatCard label="High-Risk Departments" value={String(data.high_risk_departments.filter((d) => d.avg_risk_score > 40).length)} accent="risk" />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="panel lg:col-span-2">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">Anomaly Risk Scatter</h3>
                <span className="text-xs text-parchment/40">Risk score vs anomaly score</span>
              </div>
              <div className="p-4">
                <ResponsiveContainer width="100%" height={280}>
                  <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#22304A" />
                    <XAxis type="number" dataKey="x" name="Risk Score" stroke="#6B7A94" fontSize={11} label={{ value: 'Risk Score', position: 'insideBottom', offset: -2, fill: '#6B7A94', fontSize: 11 }} />
                    <YAxis type="number" dataKey="y" name="Anomaly Score" stroke="#6B7A94" fontSize={11} />
                    <ZAxis type="number" dataKey="z" range={[40, 200]} />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null
                        const p = payload[0].payload
                        return (
                          <div className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-xs text-parchment shadow-panel">
                            <p className="font-medium">{p.department}</p>
                            <p>Risk: {p.x.toFixed(1)} · Anomaly: {p.y.toFixed(2)}</p>
                            <p className={p.isAnomaly ? 'text-risk-critical' : 'text-ledger-400'}>
                              {p.isAnomaly ? 'Flagged anomaly' : 'Normal'}
                            </p>
                          </div>
                        )
                      }}
                    />
                    <Scatter data={scatterData}>
                      {scatterData.map((d, i) => (
                        <Cell key={i} fill={d.isAnomaly ? '#E23B5D' : '#17B893'} fillOpacity={0.75} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">High-Risk Departments</h3>
              </div>
              <div className="space-y-3 p-4">
                {data.high_risk_departments.slice(0, 6).map((d) => (
                  <div key={d.department} className="flex items-center justify-between rounded-lg bg-ink-700/30 px-3 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-parchment">{d.department}</p>
                      <p className="text-xs text-parchment/40">{d.anomalies_count} anomalies · {formatINR(d.total_expenditure, true)}</p>
                    </div>
                    <RiskBadge score={d.avg_risk_score} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel mt-4">
            <div className="panel-header">
              <h3 className="font-display text-sm font-semibold text-parchment">Flagged Anomalies</h3>
              <span className="text-xs text-parchment/40">Sorted by risk score</span>
            </div>
            <div className="p-4">
              <DataTable
                columns={[
                  { key: 'department', label: 'Department' },
                  { key: 'financial_year', label: 'FY' },
                  { key: 'quarter', label: 'Qtr' },
                  { key: 'risk_score', label: 'Risk', align: 'right', render: (r) => <RiskBadge score={r.risk_score} /> },
                  { key: 'reason', label: 'Reason', render: (r) => <span className="text-xs">{r.reason || '—'}</span> },
                ]}
                rows={data.results.filter((r) => r.is_anomaly)}
              />
              {data.results.filter((r) => r.is_anomaly).length === 0 && (
                <p className="py-8 text-center text-sm text-parchment/40">No anomalies flagged in the current dataset. 🎉</p>
              )}
            </div>
          </div>
        </>
      )}
    </AppLayout>
  )
}
