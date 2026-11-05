import React from 'react'
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell,
} from 'recharts'
import { formatINR } from './UI'

const GRID_COLOR = '#22304A'
const AXIS_COLOR = '#6B7A94'
const PALETTE = ['#17B893', '#F4B740', '#3DDBB0', '#F0654C', '#6EE7C8', '#E23B5D', '#0F9A7C', '#374863']

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-xs shadow-panel">
      {label && <p className="mb-1 font-medium text-parchment/70">{label}</p>}
      {payload.map((p: any, i: number) => (
        <p key={i} className="flex items-center gap-2 text-parchment">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color || p.fill }} />
          {p.name}: <span className="font-mono">{formatINR(p.value, true)}</span>
        </p>
      ))}
    </div>
  )
}

export function DeptBarChart({ data, height = 300 }: { data: any[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="department" stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false}
          tickFormatter={(v) => formatINR(v, true)} width={60} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#EAE6DC99' }} />
        <Bar dataKey="budget" name="Budget Allocated" fill="#374863" radius={[4, 4, 0, 0]} />
        <Bar dataKey="expenditure" name="Actual Expenditure" fill="#17B893" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function TrendLineChart({ data, xKey = 'period', height = 300 }: { data: any[]; xKey?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="expGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#17B893" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#17B893" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey={xKey} stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false}
          tickFormatter={(v) => formatINR(v, true)} width={60} />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="expenditure" name="Expenditure" stroke="#17B893" strokeWidth={2} fill="url(#expGradient)" />
        <Line type="monotone" dataKey="budget" name="Budget" stroke="#F4B740" strokeWidth={1.5} strokeDasharray="4 3" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function ExpenseHeadPie({ data, height = 280 }: { data: any[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data} dataKey="amount" nameKey="expense_head"
          cx="50%" cy="50%" innerRadius={55} outerRadius={90}
          paddingAngle={2}
        >
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="#0B1120" strokeWidth={2} />)}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#EAE6DC99' }} layout="vertical" verticalAlign="middle" align="right" />
      </PieChart>
    </ResponsiveContainer>
  )
}

export function ForecastChart({ history, forecastPoint, height = 300 }: {
  history: { period_label: string; actual_expenditure: number }[]
  forecastPoint?: { period_label: string; predicted_expenditure: number; lower_bound: number | null; upper_bound: number | null }
  height?: number
}) {
  const combined = [
    ...history.map((h) => ({ period: h.period_label, actual: h.actual_expenditure })),
    ...(forecastPoint
      ? [{
          period: forecastPoint.period_label,
          forecast: forecastPoint.predicted_expenditure,
          lower: forecastPoint.lower_bound,
          upper: forecastPoint.upper_bound,
        }]
      : []),
  ]
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={combined} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="period" stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false} />
        <YAxis stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={false}
          tickFormatter={(v) => formatINR(v, true)} width={60} />
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, color: '#EAE6DC99' }} />
        <Line type="monotone" dataKey="actual" name="Actual" stroke="#3DDBB0" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#F4B740" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
