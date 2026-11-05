export type UserRole = 'admin' | 'accounts_staff' | 'hod' | 'principal'

export interface User {
  id: number
  name: string
  email: string
  role: UserRole
  department: string | null
  is_active: boolean
}

export interface DashboardSummary {
  total_budget: number
  total_expenditure: number
  remaining_budget: number
  budget_utilization_pct: number
  anomalies_detected: number
  active_departments: number
  total_transactions: number
  department_wise_spending: { department: string; budget: number; expenditure: number }[]
  quarterly_trends: { period: string; expenditure: number; budget: number }[]
  top_expense_heads: { expense_head: string; amount: number }[]
}

export interface Report {
  id: number
  user_id: number
  report_name: string
  report_year: string | null
  report_type: string
  status: string
  original_filename: string | null
  row_count: number
  upload_date: string
}

export interface UploadResponse {
  report: Report
  preview: Record<string, any>[]
  summary: {
    row_count: number
    departments: string[]
    financial_years: string[]
    quarters: string[]
    total_budget_allocated: number
    total_actual_expenditure: number
    avg_expenditure_per_record: number
    missing_values: number
  }
  warnings: string[]
}

export interface AnomalyResult {
  id: number
  transaction_id: number
  department: string
  financial_year: string
  quarter: string
  anomaly_score: number
  risk_score: number
  is_anomaly: boolean
  reason: string | null
  shap_explanation?: { feature: string; value: number; contribution: number }[] | null
}

export interface AnomalyDetectionResponse {
  total_records_analyzed: number
  anomalies_found: number
  high_risk_departments: { department: string; avg_risk_score: number; anomalies_count: number; total_expenditure: number }[]
  results: AnomalyResult[]
}

export interface ForecastOut {
  department: string
  period_label: string
  predicted_expenditure: number
  lower_bound: number | null
  upper_bound: number | null
  suggested_budget: number | null
}

export interface ForecastResponse {
  department: string | null
  history: { period_label: string; actual_expenditure: number; budget_allocated: number }[]
  forecast: ForecastOut[]
  annual_trend: { financial_year: string; total_budget: number; total_expenditure: number }[]
}

export interface ChatSource {
  content: string
  metadata: Record<string, any>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  generationMode?: 'calculated' | 'extractive' | 'gemini' | 'out_of_scope'
}
