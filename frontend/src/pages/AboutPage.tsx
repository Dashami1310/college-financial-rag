import React from 'react'
import AppLayout from '../components/AppLayout'
import { SectionHeader } from '../components/UI'

const TECH_STACK = [
  { group: 'Frontend', items: ['React.js', 'TypeScript', 'Tailwind CSS', 'Recharts', 'React Router', 'Axios'] },
  { group: 'Backend', items: ['Python', 'FastAPI', 'SQLAlchemy'] },
  { group: 'AI / ML', items: ['LangChain', 'Google Gemini API', 'Sentence Transformers', 'Scikit-Learn', 'Pandas', 'NumPy'] },
  { group: 'RAG Pipeline', items: ['LangChain', 'FAISS Vector Database', 'Recursive Text Chunking', 'Embedding Generation'] },
  { group: 'Data Processing', items: ['Pandas', 'OpenPyXL', 'CSV / Excel Processing'] },
  { group: 'Visualization', items: ['Plotly', 'Recharts', 'Matplotlib'] },
  { group: 'Database', items: ['SQLite (Development)', 'PostgreSQL'] },
]

const MODULES = [
  ['Authentication', 'Secure login with JWT authentication and role-based access control.'],
  ['Dashboard', 'Real-time financial KPIs, utilization metrics, anomalies, and expenditure trends.'],
  ['Dataset Upload', 'CSV and Excel ingestion with validation, cleaning, and preview functionality.'],
  ['Financial Analytics', 'Department-wise, quarter-wise, and year-wise expenditure analysis.'],
  ['RAG Financial Assistant', 'Natural language question answering over financial records.'],
  ['Anomaly Detection', 'Automatic identification of unusual spending patterns and outliers.'],
  ['Forecasting', 'Prediction of future expenditure and budget requirements.'],
  ['Reports', 'Generation and export of financial reports in multiple formats.'],
]

export default function AboutPage() {
  return (
    <AppLayout title="About">
      <SectionHeader
        eyebrow="Financial Analytics Platform"
        title="RAG-Based Financial Expenditure Analytics & Anomaly Detection System"
        description="AI-Powered Financial Intelligence Platform"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="panel p-6 lg:col-span-2">
          <h3 className="font-display text-sm font-semibold text-ledger-300">
            Project Description
          </h3>

          <p className="mt-2 text-sm leading-relaxed text-parchment/70">
            This platform combines advanced analytics, machine learning, and
            Retrieval-Augmented Generation (RAG) to provide intelligent
            financial expenditure monitoring and decision support.
            The system enables real-time budget tracking, expenditure analysis,
            anomaly detection, forecasting, and natural-language interaction
            with financial data through an intuitive dashboard.
          </p>

          <h3 className="mt-6 font-display text-sm font-semibold text-ledger-300">
            System Modules
          </h3>

          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {MODULES.map(([title, desc]) => (
              <div
                key={title}
                className="rounded-lg border border-ink-600/60 bg-ink-700/20 p-3"
              >
                <p className="text-sm font-medium text-parchment">{title}</p>
                <p className="mt-0.5 text-xs text-parchment/50">{desc}</p>
              </div>
            ))}
          </div>

          <h3 className="mt-6 font-display text-sm font-semibold text-ledger-300">
            Architecture
          </h3>

          <div className="mt-3 overflow-x-auto rounded-lg border border-ink-600/60 bg-ink-900/60 p-4">
            <pre className="whitespace-pre text-[11px] leading-relaxed text-parchment/60 font-mono">
{`   User ──▶ React Frontend (TypeScript + Tailwind)
              │
              │ REST API
              ▼
        FastAPI Backend ──▶ Database Layer
              │
              ├──▶ Data Processing
              │       ├──▶ Analytics Engine
              │       ├──▶ Forecasting Engine
              │       └──▶ Anomaly Detection
              │
              └──▶ RAG Pipeline
                      ├──▶ Embeddings
                      ├──▶ FAISS Vector Store
                      └──▶ Gemini API`}
            </pre>
          </div>
        </div>

        <div className="space-y-6">
          <div className="panel p-6">
            <h3 className="font-display text-sm font-semibold text-ledger-300">
              Technology Stack
            </h3>

            <div className="mt-3 space-y-3">
              {TECH_STACK.map((group) => (
                <div key={group.group}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-parchment/40">
                    {group.group}
                  </p>

                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {group.items.map((item) => (
                      <span
                        key={item}
                        className="rounded-md border border-ink-600 bg-ink-700/40 px-2 py-0.5 text-[11px] text-parchment/70"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel p-6">
            <h3 className="font-display text-sm font-semibold text-ledger-300">
              Key Features
            </h3>

            <div className="mt-3 space-y-2">
              {[
                'Real-Time Financial Dashboard',
                'Budget Utilization Monitoring',
                'Anomaly Detection',
                'Expenditure Forecasting',
                'RAG-Based Financial Assistant',
                'Interactive Data Visualizations',
                'Role-Based Access Control',
                'Report Generation & Export',
              ].map((feature) => (
                <div
                  key={feature}
                  className="rounded-lg bg-ink-700/20 px-3 py-2 text-sm text-parchment/80"
                >
                  {feature}
                </div>
              ))}
            </div>

            <div className="mt-4 border-t border-ink-600/60 pt-4 text-xs text-parchment/40">
              <p>Version 1.0</p>
              <p className="mt-1">
                Intelligent Financial Analytics Platform
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}