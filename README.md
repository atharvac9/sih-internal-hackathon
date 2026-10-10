# Clean Water Initiative — Production-Grade MVP

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js%2016-black.svg)](https://nextjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS%20v4-38bdf8.svg)](https://tailwindcss.com/)
[![Google Earth Engine](https://img.shields.io/badge/Satellite-Google%20Earth%20Engine-34A853.svg)](https://earthengine.google.com/)
[![OpenAI CLIP](https://img.shields.io/badge/Vision%20AI-OpenCLIP%20Zero--Shot-74aa9c.svg)](https://github.com/mlfoundations/open_clip)
[![CI](https://github.com/atharvac9/Clean-water-Initiative/actions/workflows/ci.yml/badge.svg)](https://github.com/atharvac9/Clean-water-Initiative/actions)

> **Field Evidence × Satellite Remote Sensing** — Production-grade ground-truth verification and condition monitoring platform for watershed interventions.

---

## 📌 Overview

Clean Water Initiative bridges spaceborne remote sensing (**Copernicus Sentinel-2 L2A Surface Reflectance**) with field-level computer vision (**OpenCLIP Zero-Shot Visual Classification**) and **EXIF metadata forensics**.

Instead of relying on static mock data, this rebuilt architecture provides:
1. **Coordinate-Agnostic GEE Engine**: Headless authentication using Google Earth Engine service account credentials (`ee.ServiceAccountCredentials`). Analyzes **any** point on the globe dynamically.
2. **Real Visual AI Classifier**: Runs zero-shot inference with OpenCLIP `ViT-B-32` over actual field uploads, reporting class distribution and model confidence.
3. **EXIF Metadata Forensics**: Audits image GPS tags, camera sensors, and capture timestamps to prevent fraudulent verification submissions.
4. **Cross-Validation Rule Engine**: Compares claimed interventions against physical vegetation (NDVI) and moisture (NDWI) delta signatures. Flags anomalies (e.g. dried reservoirs or vegetation loss).
5. **Next.js Reactive Dashboard**: Modern dark-mode interface featuring an **Orthographic 3D Globe**, a **Tactical 2D Watershed Map**, an **Ad-Hoc Coordinate Scanner**, and **WeasyPrint PDF Report Exports**.

---

## 🏗️ Architecture

```
Clean-water-Initiative/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── main.py           # Lifespan, CORS, seeds
│   │   ├── config.py         # Pydantic Settings & env configuration
│   │   ├── database.py       # SQLAlchemy async (PostgreSQL / SQLite async)
│   │   ├── models/           # Site, AnalysisResult, Photo, User ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── routers/          # /api/sites, /api/analysis, /api/photos, /api/reports, /api/health
│   │   ├── services/
│   │   │   ├── gee_service.py     # Real Sentinel-2 NDVI/NDWI queries via GEE
│   │   │   ├── classifier.py      # Real OpenCLIP inference
│   │   │   ├── cross_validator.py # Agreement & anomaly detection rules
│   │   │   ├── health_score.py    # Standardized 0-100 health scoring
│   │   │   ├── exif_checker.py    # Camera & GPS EXIF validation
│   │   │   └── storage.py         # S3 / Supabase Storage abstraction
│   │   └── utils/
│   ├── tests/                # 64 real pytest tests with strict assertions
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                 # Next.js 16 App Router Frontend
│   ├── src/
│   │   ├── app/              # Root layout, globals.css, Dashboard page
│   │   ├── components/
│   │   │   ├── Navbar.tsx           # Live telemetry status & navigation
│   │   │   ├── StatsBar.tsx         # Health metrics & anomaly counters
│   │   │   ├── Globe3D.tsx          # Interactive 3D Orthographic Globe
│   │   │   ├── WatershedMap.tsx     # Tactical 2D elevation & contour map
│   │   │   ├── SiteInspector.tsx    # Site telemetry & cross-validation inspector
│   │   │   ├── HealthGauge.tsx      # Animated radial SVG score gauge
│   │   │   ├── AdHocScannerModal.tsx# Click-anywhere Sentinel-2 query modal
│   │   │   ├── PhotoUploadModal.tsx # Field photo upload with CLIP breakdown
│   │   │   ├── SiteDirectory.tsx    # Searchable & filterable sites directory
│   │   │   └── FieldUploadView.tsx  # Dedicated photo upload view
│   │   └── lib/
│   │       ├── api.ts        # Type-safe API client with offline demo fallback
│   │       └── types.ts      # TypeScript interfaces
│   ├── Dockerfile
│   └── vercel.json
│
├── docs/
│   └── GEE_SETUP.md          # Step-by-step GEE Service Account Setup Guide
├── docker-compose.yml        # Multi-container local stack (FastAPI + Next.js + Postgres)
└── .github/workflows/ci.yml  # Automated pytest CI pipeline
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Full Stack)

```bash
docker compose up --build
```
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Option 2: Running Locally

#### 1. Start Backend

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

---

## 🧪 Automated Testing

The backend suite features **64 unit and integration tests** with assertions covering:
- Cross-validator matrix (confirmed, anomaly, inconclusive logic)
- Health score boundaries and weighted sums
- CSV schema and coordinate boundary validators
- EXIF metadata extraction and warnings
- FastAPI REST endpoints (`/health`, `/sites`, `/analysis/adhoc`)

Run all tests:
```bash
cd backend
pytest -v
```

---

## 🛰️ Google Earth Engine Setup

To connect real satellite telemetry from Copernicus Sentinel-2:
1. Create a Google Cloud Project and enable the **Earth Engine API**.
2. Create a **Service Account** and generate a JSON private key.
3. Set the environment variables in `backend/.env`:
   ```env
   GEE_SERVICE_ACCOUNT_EMAIL="your-sa@your-gcp-project.iam.gserviceaccount.com"
   GEE_SERVICE_ACCOUNT_KEY='{"type": "service_account", ...}'
   GEE_PROJECT_ID="your-gcp-project-id"
   ```
For complete details, see [**docs/GEE_SETUP.md**](docs/GEE_SETUP.md).

---

## 📄 License

MIT License. Designed for watershed restoration agencies, CSR foundations, and ecological observation teams.
