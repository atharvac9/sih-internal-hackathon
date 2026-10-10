# ⚙️ Backend Developer Guide (Isolated / Bifurcated Setup)

Welcome backend developers! The backend is a clean, modular **FastAPI** application designed for satellite telemetry ingestion (Google Earth Engine), zero-shot field photo classification (OpenCLIP), EXIF forensics, and automated compliance cross-validation.

---

## ⚡ Quick Start (1-Click)

### Windows
Double-click:
```
run_backend.bat
```
*(Or in PowerShell: `./run_backend.ps1`)*

### Terminal
```bash
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*(Or with pip: `pip install -r requirements.txt && uvicorn app.main:app --reload`)*

Interactive API documentation will be available at:
- **Swagger Docs**: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
- **ReDoc**: **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)**

---

## 🛡️ Isolated Structure in `backend/`

```
backend/
├── app/
│   ├── main.py              # FastAPI app creation, middleware, router mounts
│   ├── config.py            # Pydantic Settings & environment variables
│   ├── database.py          # SQLAlchemy 2.0 async engine & sessionmaker
│   ├── models/              # Database entities (Site, AnalysisResult, Photo, User)
│   ├── schemas/             # Pydantic request/response validation schemas
│   ├── routers/             # REST endpoint controllers
│   │   ├── sites.py         # /api/sites CRUD and seeded sites
│   │   ├── analysis.py      # /api/analysis ad-hoc Sentinel-2 scanning
│   │   ├── photos.py        # /api/photos upload & CLIP inference
│   │   ├── reports.py       # /api/reports PDF export via WeasyPrint
│   │   └── health.py        # /api/health service status checks
│   └── services/            # Core business logic & AI pipelines
│       ├── gee_service.py   # Sentinel-2 NDVI/NDWI via headless GEE auth
│       ├── classifier.py    # OpenCLIP zero-shot inference with lazy load
│       ├── exif_checker.py  # Embedded camera/GPS forensics & distance check
│       ├── health_score.py  # Health scoring formula (0-100) & grading
│       ├── cross_validator.py # Multi-modal contradiction & anomaly rules
│       └── storage.py       # Supabase storage with local base64 fallback
├── tests/                   # 64 pytest unit & integration tests
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Test dependencies
└── Dockerfile
```

---

## 🧪 Running Automated Tests

Run the complete test suite locally:
```bash
cd backend
uv run pytest -v --tb=short
```
*Current coverage: 64 test cases, 62 passed, 2 skipped (live GEE credentials).*
