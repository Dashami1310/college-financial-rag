import { api } from './client'
import type {
  User, DashboardSummary, Report, UploadResponse,
  AnomalyDetectionResponse, ForecastResponse,
} from '../types'

// ---------------- Auth ----------------
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user: User }>('/auth/login', { email, password }),
  register: (payload: { name: string; email: string; password: string; role?: string; department?: string }) =>
    api.post<User>('/auth/register', payload),
  me: () => api.get<User>('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

// ---------------- Dashboard ----------------
export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/dashboard/summary'),
}

// ---------------- Upload ----------------
export const uploadApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<UploadResponse>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  datasets: () => api.get<Report[]>('/upload/datasets'),
}

// ---------------- Analytics ----------------
export const analyticsApi = {
  filters: () => api.get<{ financial_years: string[]; quarters: string[]; departments: string[] }>('/analytics/filters'),
  breakdown: (params: { financial_year?: string; quarter?: string; department?: string }) =>
    api.get('/analytics/breakdown', { params }),
  utilization: (params: { financial_year?: string; quarter?: string; department?: string }) =>
    api.get('/analytics/utilization', { params }),
  compare: (departments: string[]) =>
    api.get('/analytics/compare', { params: { departments: departments.join(',') } }),
}

// ---------------- Anomaly ----------------
export const anomalyApi = {
  detect: (params?: { financial_year?: string; department?: string }) =>
    api.get<AnomalyDetectionResponse>('/anomaly/detect', { params }),
}

// ---------------- Forecast ----------------
export const forecastApi = {
  get: (department?: string) =>
    api.get<ForecastResponse>('/forecast', { params: department ? { department } : {} }),
}

// ---------------- RAG ----------------
export const ragApi = {
  chat: (question: string) => api.post('/rag/chat', { question }),
  history: () => api.get('/rag/history'),
  reindex: () => api.post('/rag/reindex'),
}

// ---------------- Reports ----------------
export const reportsApi = {
  generate: (payload: {
    report_type: string
    financial_year?: string
    quarter?: string
    department?: string
    export_format: string
  }) => api.post('/reports/generate', payload, { responseType: 'blob' }),
}
