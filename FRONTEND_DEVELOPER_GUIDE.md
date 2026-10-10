# 🎨 Frontend Developer Guide (Isolated / Bifurcated Setup)

Welcome frontend developers! The frontend of the **Clean Water Initiative** is completely decoupled from the Python backend. You can build, style, modify components, and test UI flows **without installing Python or running the backend**.

---

## ⚡ Quick Start (1-Click)

### Windows
Double-click:
```
run_frontend.bat
```
*(Or in PowerShell: `./run_frontend.ps1`)*

### Mac / Linux / Terminal
```bash
cd frontend
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🛡️ Zero-Risk / Isolated Development

- **No Backend Required**: If the FastAPI backend is not running, the frontend automatically activates client-side simulation fallbacks (`FALLBACK_DEMO_SITES` in `src/lib/api.ts`).
- **All Frontend Code is Isolated in `frontend/`**:
  ```
  frontend/
  ├── src/
  │   ├── app/                 # Next.js App Router (pages, layout, globals.css)
  │   │   ├── layout.tsx
  │   │   ├── page.tsx         # Main dashboard page
  │   │   └── globals.css      # Design tokens & Tailwind CSS
  │   ├── components/          # Reusable UI components
  │   │   ├── Navbar.tsx
  │   │   ├── StatsBar.tsx
  │   │   ├── WatershedMap.tsx # 2D Tactical satellite map
  │   │   ├── Globe3D.tsx      # 3D Orthographic globe
  │   │   ├── SiteInspector.tsx# Site details & health breakdown
  │   │   ├── HealthGauge.tsx  # Radial health score SVG gauge
  │   │   ├── SiteDirectory.tsx# Sites table & filter
  │   │   ├── FieldUploadView.tsx # Photo verification view
  │   │   ├── AdHocScannerModal.tsx
  │   │   └── PhotoUploadModal.tsx
  │   └── lib/
  │       ├── api.ts           # API connector with automatic offline fallbacks
  │       └── types.ts         # TypeScript data contracts
  ├── package.json
  ├── tsconfig.json
  └── next.config.ts
  ```
- **Backend Safety**: You can safely edit any file inside `frontend/` without affecting the Python backend, database, GEE models, or CI tests.

---

## 🔌 Connecting to the Backend (Optional)

When you want to test against live satellite data and real CLIP model inference:
1. Double click `run_backend.bat` (starts FastAPI on `http://127.0.0.1:8000`).
2. The frontend automatically detects the live backend and uses real endpoints!

---

## 🧪 Testing Your Frontend Build

Before pushing changes:
```bash
cd frontend
npm run build
```
Ensure there are zero TypeScript and lint errors.
