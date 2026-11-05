import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader, StatCard, Loading, EmptyState, formatINR } from '../components/UI'
import { DeptBarChart, TrendLineChart, ExpenseHeadPie } from '../components/Charts'
import { dashboardApi } from '../api/endpoints'
import { api } from '../api/client'
import type { DashboardSummary } from '../types'
import { useNavigate } from 'react-router-dom'

interface ReportItem {
  id: number
  report_name: string
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const [reports, setReports] = useState<ReportItem[]>([])
  const [selectedReport, setSelectedReport] = useState<string>('')

  const navigate = useNavigate()

  useEffect(() => {
    loadReports()
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [selectedReport])

  const loadReports = async () => {
    try {
      const res = await api.get('/upload/datasets')
      setReports(res.data)
    } catch (err) {
      console.error(err)
    }
  }
  const loadDashboard = async () => {
  setLoading(true)

  try {
    let res

    if (selectedReport) {
      console.log("Selected Report ID:", selectedReport)

      res = await api.get(
        `/dashboard/summary?report_id=${selectedReport}`
      )
    } else {
      res = await dashboardApi.summary()
    }

    console.log("Dashboard Response:", res.data)

    setData(res.data)
  } catch (err) {
    console.error("Dashboard Error:", err)
  } finally {
    setLoading(false)
  }
}
  return (
    <AppLayout title="Financial Dashboard">
      <SectionHeader
        eyebrow="Overview"
        title="Institution Financial Health"
        description="Real-time expenditure, budget utilization, and anomaly signals across all departments."
      />

      <div className="panel mb-4">
        <div className="p-4">
          <label className="mb-2 block text-sm text-parchment/70">
            Select Dataset
          </label>

          <select
            value={selectedReport}
            onChange={(e) => setSelectedReport(e.target.value)}
            className="w-full rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-parchment"
          >
            <option value="">All Uploaded Datasets</option>

            {reports.map((report) => (
              <option key={report.id} value={report.id}>
                {report.report_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <Loading />
      ) : !data || data.total_transactions === 0 ? (
        <div className="panel">
          <EmptyState
            title="No financial data yet"
            description="Upload a CSV or Excel expenditure dataset to populate the dashboard, analytics, forecasts, and RAG assistant."
            action={
              <button
                onClick={() => navigate('/upload')}
                className="btn-primary mt-2"
              >
                Upload dataset
              </button>
            }
          />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Total Budget"
              value={formatINR(data.total_budget, true)}
              accent="neutral"
              sublabel="Allocated across all departments"
            />
            <StatCard
              label="Total Expenditure"
              value={formatINR(data.total_expenditure, true)}
              accent="ledger"
              sublabel={`${data.budget_utilization_pct.toFixed(1)}% of budget used`}
            />
            <StatCard
              label="Remaining Budget"
              value={formatINR(data.remaining_budget, true)}
              accent={data.remaining_budget < 0 ? 'risk' : 'neutral'}
              sublabel="Available across institution"
            />
            <StatCard
              label="Anomalies Detected"
              value={String(data.anomalies_detected)}
              accent={data.anomalies_detected > 0 ? 'amber' : 'ledger'}
              sublabel="Flagged by Isolation Forest"
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              label="Budget Utilization"
              value={`${data.budget_utilization_pct.toFixed(1)}%`}
              accent="neutral"
            />
            <StatCard
              label="Active Departments"
              value={String(data.active_departments)}
              accent="neutral"
            />
            <StatCard
              label="Total Transactions"
              value={data.total_transactions.toLocaleString('en-IN')}
              accent="neutral"
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="panel lg:col-span-2">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">
                  Department-wise Spending
                </h3>
              </div>
              <div className="p-4">
                <DeptBarChart data={data.department_wise_spending} />
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">
                  Top Expense Heads
                </h3>
              </div>
              <div className="p-4">
                {data.top_expense_heads.length > 0 ? (
                  <ExpenseHeadPie data={data.top_expense_heads} />
                ) : (
                  <p className="py-10 text-center text-sm text-parchment/40">
                    No expense head data available.
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 panel">
            <div className="panel-header">
              <h3 className="font-display text-sm font-semibold text-parchment">
                Quarterly Spending Trends
              </h3>
            </div>
            <div className="p-4">
              <TrendLineChart data={data.quarterly_trends} />
            </div>
          </div>
        </>
      )}
    </AppLayout>
  )
}