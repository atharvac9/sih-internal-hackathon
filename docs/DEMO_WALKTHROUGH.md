# 🛰️ Watershed Photo-Satellite Fusion — Demo Walkthrough

> **Production MVP** — Ground Field Evidence × Copernicus Sentinel-2 Remote Sensing

---

## 🌟 Executive Summary

Clean Water Initiative delivers an end-to-end multi-modal verification layer for watershed restoration interventions. Field workers submit geo-tagged photographs of interventions (check dams, farm ponds, plantations), and the platform cross-references ground-level visual evidence against temporal multi-spectral Sentinel-2 satellite imagery (NDVI and NDWI) at that exact coordinate over time.

---

## 📸 Visual Demo & Architecture Overview

### 1. Main Dashboard — Dual 2D/3D Tactical Reconnaissance
The dashboard features an interactive tactical interface:
- **Tactical 2D Map (`WatershedMap.tsx`)**: High-resolution satellite tiles (Esri World Imagery) and dark tactical cartography with exact Web Mercator coordinate placement, 500m buffer zone overlays, and click-anywhere coordinate inspection.
- **Orthographic 3D Globe (`Globe3D.tsx`)**: Interactive rotating WebGL/Canvas sphere displaying continental landmasses, latitude/longitude graticules, atmospheric rim glow, and plotted site markers.
- **Top Metrics Bar**: Live indicators for monitored sites, confirmed cross-matches, flagged anomalies, and average watershed health index.

---

### 2. S06 Anomaly Detection — Ground-Truth Verification
A field worker claims site **S06** is a constructed **Farm Pond**. Our platform cross-examines the claim using multi-spectral satellite imagery and OpenCLIP zero-shot photo classification, instantly flagging a high-priority mismatch.

#### The Evidence Breakdown for Site S06:
| Modality | Expected (Claimed: Farm Pond) | Detected Reality | Status |
| :--- | :--- | :--- | :--- |
| **Field Photo** | Farm pond water harvesting | Classified as **Degraded Land / Barren** | 🚨 Mismatch |
| **NDWI (Water)** | Positive water accumulation | `0.230` → `-0.190` (▼ Moisture loss) | 🚨 Anomaly |
| **NDVI (Vegetation)** | Stabilizing vegetation around reservoir | `0.230` → `0.145` (▼ Biomass drop) | 🚨 Anomaly |
| **Health Score** | Nominal 70+ | **32 / 100 (Grade F)** | 🚨 High Risk |

#### 3 Automated Flags Raised:
1. `ANOMALY: Satellite moisture index (NDWI) decreased after reported farm pond construction`
2. `Vegetation vigor loss detected in 500m buffer zone`
3. `Ground photo confirms dried barren soil rather than water reservoir`

---

### 3. On-Demand Ad-Hoc Satellite Scanner
Clicking any point on either the 2D Tactical Map or the 3D Globe opens the **Sentinel-2 On-Demand Scanner Modal**, enabling administrators to:
- Read out exact latitude and longitude
- Select a claimed intervention type
- Configure observation buffer radius ($100\text{m} - 2000\text{m}$)
- Select a baseline date for before/after delta analysis vs current snapshot
- Execute live satellite queries and save locations to the permanent monitoring network

---

### 4. Field Photo Upload & EXIF Forensics
Field verification uploads undergo automated two-stage analysis:
- **OpenCLIP Model (`ViT-B-32`)**: Produces a softmax probability distribution over 5 intervention types without domain fine-tuning.
- **EXIF Metadata Forensics**: Audits camera sensor model, capture timestamp, and embedded GPS geotags to prevent fraudulent submissions.

---

### 5. Official PDF Report Export
Clicking "Export Official PDF Report" triggers `GET /api/reports/{site_id}/pdf` on the FastAPI backend, generating an auditable, styled PDF report via WeasyPrint complete with site metadata, satellite trends, photo proof, and anomaly flags.
