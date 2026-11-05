# BIET FinAssist — RAG-Based College Financial Expenditure Analytics & Anomaly Detection System

A full-stack, AI-powered financial analytics platform for technical institutions. It combines
**Retrieval-Augmented Generation** (natural-language financial Q&A), **Isolation Forest anomaly
detection**, and **time-series forecasting** into one live financial command center.

Built as a B.E. Artificial Intelligence & Machine Learning major project. The project includes
a React web client and a Flutter client for Android and web.

---

## ✨ Features

| Module                      | What it does                                                                                                            |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Authentication**          | JWT login with role-based access — Admin, Accounts Staff, HOD, Principal                                                |
| **Dashboard**               | Total budget, expenditure, utilization %, anomalies, department & quarterly trends                                      |
| **Dataset Upload**          | CSV/Excel ingestion with column validation, cleaning, and live preview                                                  |
| **Financial Analytics**     | Filter by department / quarter / financial year; budget utilization & comparisons                                       |
| **RAG Financial Assistant** | Chat interface answering questions like _"Which department overspent in Q2?"_ using FAISS retrieval + Gemini generation |
| **Anomaly Detection**       | Isolation Forest flags overspending, budget violations, outlier transactions, high-risk departments                     |
| **Forecasting**             | Predicts next-quarter expenditure, department budget needs, and annual trends                                           |
| **Reports**                 | Quarterly / Department / Summary reports exportable as PDF or Excel                                                     |
| **About**                   | Project description, architecture, and tech stack                                                                       |

---

## 🧱 Tech Stack

- **Web frontend:** React.js, TypeScript, Tailwind CSS, Recharts, React Router, Axios
- **Mobile/web app:** Flutter, Dart, Dio
- **Backend:** Python, FastAPI, SQLAlchemy
- **AI/ML:** LangChain, Google Gemini API, Sentence Transformers, Scikit-Learn, Pandas, NumPy
- **RAG Pipeline:** LangChain + FAISS + Recursive Text Chunking + Embedding Generation
- **Data Processing:** Pandas, OpenPyXL, CSV/Excel Processing
- **Visualization:** Recharts (frontend), Plotly/Matplotlib-ready (backend)
- **Database:** SQLite by default; swap to PostgreSQL by changing one env variable

---

## 🏗️ Architecture

```
   User ──▶ Flutter App (Android / Web) or React Web Frontend
              │  Axios / REST (JWT auth)
              ▼
        FastAPI Backend ──▶ SQLite / PostgreSQL
              │
              ├──▶ Pandas Processing Layer
              │        ├──▶ ML Models
              │        │      • Isolation Forest (anomaly detection)
              │        │      • Linear Regression / Weighted MA (forecasting)
              │        └──▶ RAG Pipeline
              │                 • Recursive Text Chunking
              │                 • Sentence-Transformer Embeddings
              │                 • FAISS Vector Store
              │                 • Google Gemini (generation)
              └──▶ Report Generator (ReportLab PDF / OpenPyXL Excel)
```

---

## 📁 Project Structure

```
college-financial-rag/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings (DB URL, secrets, RAG params)
│   │   ├── database.py           # SQLAlchemy engine/session
│   │   ├── models.py             # ORM models (users, records, anomalies, forecasts...)
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── auth.py               # JWT + RBAC
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── upload.py
│   │   │   ├── analytics.py
│   │   │   ├── anomaly.py
│   │   │   ├── forecast.py
│   │   │   ├── rag.py
│   │   │   └── reports.py
│   │   ├── services/
│   │   │   ├── data_processing.py    # CSV/Excel ingestion, validation, cleaning
│   │   │   ├── anomaly_detection.py  # Isolation Forest pipeline
│   │   │   ├── forecasting.py        # Time-series forecasting
│   │   │   ├── rag_pipeline.py       # FAISS + Gemini RAG pipeline
│   │   │   └── report_generator.py   # PDF / Excel report generation
│   │   ├── data/                 # SQLite DB + sample dataset (generated)
│   │   ├── uploads/               # Uploaded raw files
│   │   └── vectorstore/           # Persisted FAISS index
│   ├── seed_data.py               # Creates demo users + synthetic sample dataset
│   ├── requirements.txt
│   └── .env.example
├── frontend/
    ├── src/
    │   ├── api/                   # Axios client + endpoint functions
    │   ├── components/            # Sidebar, Topbar, Charts, DataTable, UI primitives
    │   ├── context/                # AuthContext (JWT + RBAC)
    │   ├── pages/                  # Login, Dashboard, Upload, Analytics, RAG Assistant,
    │   │                            Anomalies, Forecast, Reports, About
    │   ├── types/                  # Shared TypeScript types
    │   ├── App.tsx                 # Routing
    │   └── main.tsx
    ├── tailwind.config.js
    ├── vite.config.ts
    └── package.json
└── flutter_app/
    ├── lib/                   # Flutter login, dashboard, analytics, reports and assistant
    └── pubspec.yaml
```

---

## 📱 Flutter app (Android and web)

The Flutter client supports Android phones, Android emulators, and web. Install
the current stable Flutter SDK (which includes Dart) and Android Studio with the
Android SDK. For a physical phone, enable Developer options and USB debugging;
for web, install Google Chrome. Check the setup and accept Android SDK licenses:

```powershell
flutter doctor
flutter doctor --android-licenses
Set-Location flutter_app
flutter pub get
```

Start the FastAPI backend in a separate terminal using the steps in
[Getting Started](#-getting-started). Keep it running while using the app.

### Run the app

From `flutter_app`, list available devices and run on an Android emulator or
USB-connected phone:

```powershell
flutter devices
flutter run -d <device-id> -t lib/main.dart
```

For Flutter web, run:

```powershell
flutter run -d chrome -t lib/main.dart --web-port 8080
```

The app's default backend URL is `http://10.0.2.2:8000` on Android and
`http://127.0.0.1:8000` on web. On the sign-in screen, choose **Configure
server** to change it. The app adds `/api` automatically, so enter the server
root URL, such as `http://192.168.1.10:8000`.

### Build and install an Android APK

Build a debug APK from `flutter_app`:

```powershell
flutter pub get
flutter build apk --debug
```

The APK is at `build\app\outputs\flutter-apk\app-debug.apk`. Install it directly
to a USB-connected device with Android platform tools:

```powershell
adb install -r build\app\outputs\flutter-apk\app-debug.apk
```

Alternatively, transfer the APK to the phone, open it, and approve installation
from that source when Android prompts. This is a development build, not a Play
Store release.

### Connect a physical phone to the local backend

The Android emulator can use `10.0.2.2` to reach the development computer. A
physical phone needs the computer's private network address:

1. Connect the phone and computer to the same trusted Wi-Fi network. In the
   `backend` directory, start the API so it accepts connections from the LAN:

   ```powershell
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. Run `ipconfig` on the computer and note its private IPv4 address. If Windows
   Firewall blocks the connection, allow inbound TCP port 8000 on the **Private**
   network only.

3. In the app, choose **Configure server** and enter
   `http://<PC-private-IPv4>:8000` (replace the placeholder with the address
   from `ipconfig`). The backend computer must remain on and reachable while the
   app is using it.

### Sign in and use the app

- Sign in with an account already provisioned by the backend, or use the
  **Create accounts-staff account** option on the sign-in screen. Signup asks
  for a name, email, password (at least eight characters), and optionally a
  department. Public signup creates an accounts-staff account; privileged roles
  must be provisioned through the trusted backend setup process.
- Use the app navigation to open the dashboard, analytics, anomaly detection,
  forecasts, financial assistant, and reports. Upload supported CSV/Excel
  financial data or audit PDFs, then view results and export available PDF/Excel
  reports.
- Keep the backend running during use. For a deployed app, configure a deployed
  HTTPS API and create a signed release build; do not distribute the debug APK
  as a production app.

Flutter web development uses port 8080, which is included in the backend's local
CORS allowlist.

---

## 🚀 Getting Started

### 1. Backend

#### Windows (PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python seed_data.py
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
in that terminal and activate the environment again. Alternatively, skip activation and run
`.\venv\Scripts\python.exe -m pip install -r requirements.txt`, then use that Python executable
for Alembic, `seed_data.py`, and Uvicorn.

The example `.env` uses a local SQLite database, so no PostgreSQL server or database credentials
are needed for a local demo. If you already copied an older `.env.example`, update its
`DATABASE_URL` to `sqlite:///./app/data/college_finance.db`. For PostgreSQL, replace the example
URL with your real database URL and make sure that server is running and accepting connections.

#### macOS / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python seed_data.py
python -m uvicorn app.main:app --reload --port 8000
```

API docs: **http://localhost:8000/docs**

Generate a signing key before deployment with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
and set it as `SECRET_KEY` in your private `.env`. Public signup only creates accounts-staff
accounts; provision administrator and other privileged accounts through the trusted seed/setup flow.

> **Note on the RAG assistant:** If `GOOGLE_API_KEY` is left blank, the assistant still works —
> it falls back to an extractive answer built directly from the retrieved FAISS context, so the
> whole pipeline (upload → chunk → embed → retrieve → answer) is demoable offline. It declines
> questions unrelated to uploaded college financial data and audit reports. Add a Gemini key in
> `.env` to unlock fully generative natural-language answers.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: **http://localhost:5173** (proxies `/api` to the backend on port 8000)

### 3. Sign in

Use an account provisioned by the backend setup process, or create an
accounts-staff account from the Flutter app's sign-in screen. Public signup
does not grant administrator or other privileged roles.

---

## 🗄️ Dataset Schema

Upload a CSV or Excel file with these columns (header names are flexible — common aliases like
"FY", "Dept", "Qtr" are auto-normalized):

| Column                 | Type                                                     |
| ---------------------- | -------------------------------------------------------- |
| Financial Year         | text, e.g. `2025-2026`                                   |
| Quarter                | `Q1` \| `Q2` \| `Q3` \| `Q4`                             |
| Department             | one of the 12 supported departments                      |
| Budget Allocated       | number                                                   |
| Actual Expenditure     | number                                                   |
| Remaining Budget       | number (auto-computed if omitted)                        |
| Major Expense Head     | text                                                     |
| Number of Transactions | integer                                                  |
| Vendor                 | text                                                     |
| Approval Status        | `Approved` \| `Pending` \| `Rejected`                    |
| Anomalies Detected     | boolean (also computed by the ML pipeline)               |
| Forecast Next Quarter  | number (optional; the forecasting module generates this) |

**Supported departments:** AIML, CSE, ISE, ECE, EEE, Mechanical, Civil, MBA, Library,
Administration, Placement Cell, Hostel.

---

## 🔄 Switching to PostgreSQL

The app is written entirely against standard SQLAlchemy — no SQLite-specific code. To move to
PostgreSQL in production, install `psycopg2-binary` and change one line in `.env`:

```
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/college_finance
```

No other code changes are required.

---

## 🧪 What's been tested

The backend has been exercised end-to-end (not just written): dataset ingestion → cleaning →
Isolation Forest anomaly detection → linear-regression forecasting → PDF/Excel report generation,
plus the full FastAPI app (auth, RBAC enforcement, all 8 routers) via `TestClient`. The frontend
has been installed, type-checked with `tsc`, and built with `vite build` with zero errors.

---
