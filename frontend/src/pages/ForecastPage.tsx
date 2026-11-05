import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader, Loading, formatINR } from '../components/UI'
import { FilterSelect, DataTable } from '../components/DataTable'
import { ForecastChart, TrendLineChart } from '../components/Charts'
import { forecastApi, analyticsApi } from '../api/endpoints'
import type { ForecastResponse } from '../types'

export default function ForecastPage() {
  const [departments, setDepartments] = useState<string[]>([])
  const [dept, setDept] = useState('')
  const [data, setData] = useState<ForecastResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsApi.filters().then((res) => setDepartments(res.data.departments))
  }, [])

  useEffect(() => {
    setLoading(true)
    forecastApi.get(dept || undefined).then((res) => setData(res.data)).finally(() => setLoading(false))
  }, [dept])

  return (
    <AppLayout title="Forecasting">
      <SectionHeader
        eyebrow="Time-Series Prediction"
        title="Expenditure Forecasting"
        description="Predicts next-quarter expenditure, department budget requirements, and annual financial trends."
      />

      <div className="panel mb-6 flex flex-wrap items-end gap-4 p-4">
        <div className="w-56">
          <FilterSelect label="Department (optional)" value={dept} onChange={setDept} options={departments} placeholder="All departments" />
        </div>
      </div>

      {loading ? (
        <Loading label="Running forecast models…" />
      ) : !data ? null : (
        <>
          <div className="panel mb-4">
            <div className="panel-header">
              <h3 className="font-display text-sm font-semibold text-parchment">Annual Financial Trend</h3>
            </div>
            <div className="p-4">
              <TrendLineChart
                data={data.annual_trend.map((t) => ({ period: t.financial_year, expenditure: t.total_expenditure, budget: t.total_budget }))}
                xKey="period"
              />
            </div>
          </div>

          {dept && data.forecast.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="panel lg:col-span-2">
                <div className="panel-header">
                  <h3 className="font-display text-sm font-semibold text-parchment">{dept} — Expenditure Forecast</h3>
                  <span className="text-xs text-parchment/40">Next period: {data.forecast[0].period_label}</span>
                </div>
                <div className="p-4">
                  <ForecastChart
                    history={data.history.map((h) => ({ period_label: h.period_label, actual_expenditure: h.actual_expenditure }))}
                    forecastPoint={data.forecast[0]}
                  />
                </div>
              </div>
              <div className="panel p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-parchment/40">Predicted Expenditure</p>
                <p className="stat-figure mt-1 text-2xl font-semibold text-risk-mid">{formatINR(data.forecast[0].predicted_expenditure, true)}</p>
                <p className="mt-1 text-xs text-parchment/40">
                  Range: {formatINR(data.forecast[0].lower_bound ?? 0, true)} – {formatINR(data.forecast[0].upper_bound ?? 0, true)}
                </p>
                <div className="mt-4 border-t border-ink-600/60 pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-parchment/40">Suggested Budget</p>
                  <p className="stat-figure mt-1 text-xl font-semibold text-ledger-300">{formatINR(data.forecast[0].suggested_budget ?? 0, true)}</p>
                  <p className="mt-1 text-xs text-parchment/40">Forecast + 10% buffer</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="panel">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">Next-Quarter Forecast — All Departments</h3>
              </div>
              <div className="p-4">
                <DataTable
                  columns={[
                    { key: 'department', label: 'Department' },
                    { key: 'period_label', label: 'Forecast Period' },
                    { key: 'predicted_expenditure', label: 'Predicted', align: 'right', render: (r) => formatINR(r.predicted_expenditure) },
                    { key: 'suggested_budget', label: 'Suggested Budget', align: 'right', render: (r) => formatINR(r.suggested_budget ?? 0) },
                    { key: 'lower_bound', label: 'Range', align: 'right', render: (r) => (
                      <span className="text-xs text-parchment/50">
                        {formatINR(r.lower_bound ?? 0, true)} – {formatINR(r.upper_bound ?? 0, true)}
                      </span>
                    ) },
                  ]}
                  rows={data.forecast}
                  keyField="department"
                />
              </div>
            </div>
          )}
        </>
      )}
    </AppLayout>
  )
}
