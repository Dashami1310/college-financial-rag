import React, { useEffect, useState } from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader, Loading, formatINR } from '../components/UI'
import { FilterSelect, DataTable } from '../components/DataTable'
import { DeptBarChart, ExpenseHeadPie } from '../components/Charts'
import { analyticsApi } from '../api/endpoints'

export default function AnalyticsPage() {
  const [filters, setFilters] = useState<{ financial_years: string[]; quarters: string[]; departments: string[] }>({
    financial_years: [], quarters: [], departments: [],
  })
  const [fy, setFy] = useState('')
  const [quarter, setQuarter] = useState('')
  const [dept, setDept] = useState('')
  const [breakdown, setBreakdown] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsApi.filters().then((res) => setFilters(res.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    analyticsApi.breakdown({
      financial_year: fy || undefined,
      quarter: quarter || undefined,
      department: dept || undefined,
    }).then((res) => setBreakdown(res.data)).finally(() => setLoading(false))
  }, [fy, quarter, dept])

  return (
    <AppLayout title="Financial Analytics">
      <SectionHeader
        eyebrow="Deep Dive"
        title="Expenditure Breakdown & Comparison"
        description="Filter by financial year, quarter, and department to analyze budget utilization and spending patterns."
      />

      <div className="panel mb-6 flex flex-wrap gap-4 p-4">
        <div className="w-44">
          <FilterSelect label="Financial Year" value={fy} onChange={setFy} options={filters.financial_years} />
        </div>
        <div className="w-36">
          <FilterSelect label="Quarter" value={quarter} onChange={setQuarter} options={filters.quarters} />
        </div>
        <div className="w-48">
          <FilterSelect label="Department" value={dept} onChange={setDept} options={filters.departments} />
        </div>
        {(fy || quarter || dept) && (
          <div className="flex items-end">
            <button onClick={() => { setFy(''); setQuarter(''); setDept('') }} className="btn-secondary">
              Clear filters
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <Loading />
      ) : !breakdown || breakdown.records === 0 ? (
        <div className="panel p-12 text-center text-sm text-parchment/40">No records match the selected filters.</div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="panel lg:col-span-2">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">Budget vs Expenditure by Department</h3>
              </div>
              <div className="p-4">
                <DeptBarChart data={breakdown.by_department.map((d: any) => ({
                  department: d.department, budget: d.budget_allocated, expenditure: d.actual_expenditure,
                }))} />
              </div>
            </div>
            <div className="panel">
              <div className="panel-header">
                <h3 className="font-display text-sm font-semibold text-parchment">Expense Head Distribution</h3>
              </div>
              <div className="p-4">
                {breakdown.by_expense_head.length > 0 ? (
                  <ExpenseHeadPie data={breakdown.by_expense_head.slice(0, 6).map((h: any) => ({
                    expense_head: h.major_expense_head, amount: h.actual_expenditure,
                  }))} />
                ) : (
                  <p className="py-10 text-center text-sm text-parchment/40">No data.</p>
                )}
              </div>
            </div>
          </div>

          <div className="panel mt-4">
            <div className="panel-header">
              <h3 className="font-display text-sm font-semibold text-parchment">Department Summary Table</h3>
              <span className="text-xs text-parchment/40">{breakdown.records} matching records</span>
            </div>
            <div className="p-4">
              <DataTable
                keyField="department"
                columns={[
                  { key: 'department', label: 'Department' },
                  { key: 'budget_allocated', label: 'Budget', align: 'right', render: (r) => formatINR(r.budget_allocated) },
                  { key: 'actual_expenditure', label: 'Expenditure', align: 'right', render: (r) => formatINR(r.actual_expenditure) },
                  { key: 'remaining_budget', label: 'Remaining', align: 'right', render: (r) => (
                    <span className={r.remaining_budget < 0 ? 'text-risk-critical' : ''}>{formatINR(r.remaining_budget)}</span>
                  ) },
                  { key: 'transactions', label: 'Transactions', align: 'right' },
                  { key: 'utilization', label: 'Utilization', align: 'right', render: (r) => (
                    <span>{r.budget_allocated ? ((r.actual_expenditure / r.budget_allocated) * 100).toFixed(1) : '0'}%</span>
                  ) },
                ]}
                rows={breakdown.by_department}
              />
            </div>
          </div>
        </>
      )}
    </AppLayout>
  )
}
