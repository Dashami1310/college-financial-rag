import React, { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const UploadPage = lazy(() => import('./pages/UploadPage'))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const RagAssistantPage = lazy(() => import('./pages/RagAssistantPage'))
const AnomaliesPage = lazy(() => import('./pages/AnomaliesPage'))
const ForecastPage = lazy(() => import('./pages/ForecastPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))

export default function App() {
  return (
    <Suspense fallback={<div role="status" className="p-6 text-sm text-parchment/60">Loading page…</div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/upload" element={
          <ProtectedRoute roles={['admin', 'accounts_staff']}><UploadPage /></ProtectedRoute>
        } />
        <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="/assistant" element={<ProtectedRoute><RagAssistantPage /></ProtectedRoute>} />
        <Route path="/anomalies" element={<ProtectedRoute><AnomaliesPage /></ProtectedRoute>} />
        <Route path="/forecast" element={<ProtectedRoute><ForecastPage /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
        <Route path="/about" element={<ProtectedRoute><AboutPage /></ProtectedRoute>} />

        <Route path="*" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      </Routes>
    </Suspense>
  )
}
