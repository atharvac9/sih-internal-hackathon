# 🚀 Clean Water Initiative — Deployment Guide

Production deployment guide for the Clean Water Initiative multi-container architecture.

---

## 🏗️ Architecture Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 Async, Pydantic Settings, WeasyPrint, OpenCLIP, Google Earth Engine API
- **Frontend**: Next.js 16 (React 19, TypeScript), Tailwind CSS v4, Lucide Icons, Slippy Map Tiles, HTML5 Canvas 3D Orthographic Globe
- **Database**: PostgreSQL 16 (or async SQLite for local lightweight development)
- **Containerization**: Docker Compose, Multi-stage Dockerfiles

---

## 🐳 1. Local Deployment with Docker Compose

The fastest way to spin up the entire system locally:

```bash
docker compose up --build
```

### Containers Started:
1. `backend`: FastAPI app running on `http://localhost:8000` (Swagger docs at `/docs`)
2. `frontend`: Next.js production server running on `http://localhost:3000`
3. `db`: PostgreSQL 16 Alpine on port `5432` with persistent data volume

---

## ☁️ 2. Cloud Deployment

### Backend (Render / Railway / Fly.io)

1. Create a new Web Service pointing to `backend/Dockerfile`.
2. Configure Environment Variables:
   ```env
   PORT=8000
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
   CORS_ORIGINS=https://your-frontend.vercel.app
   GEE_SERVICE_ACCOUNT_EMAIL="your-sa@your-gcp-project.iam.gserviceaccount.com"
   GEE_SERVICE_ACCOUNT_KEY='{"type": "service_account", ...}'
   GEE_PROJECT_ID="your-gcp-project-id"
   SUPABASE_URL="https://your-project.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
   ```
3. Health Check Path: `/api/health`

### Frontend (Vercel)

1. Connect your repository to Vercel with Root Directory set to `frontend`.
2. Set Environment Variable:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com/api
   ```
3. Deploy. The included `vercel.json` will automatically configure routing.

---

## 🛰️ 3. Google Earth Engine Service Account Setup

Refer to [**docs/GEE_SETUP.md**](GEE_SETUP.md) for full step-by-step instructions to create and register your GCP service account with Google Earth Engine.
