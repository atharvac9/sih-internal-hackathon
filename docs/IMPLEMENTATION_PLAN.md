# Watershed Photo-Satellite Fusion MVP — Implementation Plan

Build a Streamlit-based MVP that fuses geo-tagged field photos of watershed interventions with Sentinel-2 satellite data (NDVI/NDWI) to auto-validate claimed interventions and flag anomalies.

## User Review Required

> [!IMPORTANT]
> **GEE Authentication**: The plan assumes you have a Google Earth Engine account already registered and authenticated (`earthengine authenticate` has been run). If not, we'll need to handle that first before Step 1 can be verified.

> [!IMPORTANT]
> **CLIP vs ResNet18**: The plan uses **OpenAI CLIP** (via `transformers` + `torch`) for zero-shot classification of field photos into the 5 classes. This avoids the need for any training data and gets a working demo fastest. If you'd prefer ResNet18 with transfer learning instead, let me know — but CLIP is the right call for a hackathon with no labeled training set.

> [!WARNING]
> **Sample photos**: We need 8 field photos (JPEGs) of check dams, farm ponds, plantations, degraded land, and water bodies. I'll generate placeholder images using the image generation tool to create realistic-looking field photos for the demo dataset. If you have real photos, we can swap them in later.

## Open Questions

1. **GEE project ID** — Do you have a specific GEE cloud project ID to use for `ee.Initialize(project='...')`? Or should I use the default authentication flow?
2. **Region preference** — The sample coordinates are set in **Maharashtra** (Ahmednagar/Pune watershed region, a well-known watershed development area). Should I use a different region?
3. **Time window** — Planning to use `T0 = 2024-01-01 to 2024-03-31` (pre-monsoon baseline) and `T_now = 2026-06-01 to 2026-08-31` (current monsoon). Good?

---

## Proposed Changes

### Project Structure

```
Clean-water-Initiative/
├── app.py                     # Main Streamlit entry point
├── requirements.txt           # All dependencies
├── README.md                  # Setup + run instructions
├── config.py                  # Constants, GEE project, time windows
├── data/
│   ├── sites.csv              # 8 sites: lat, lon, date, activity_type, photo_filename
│   └── photos/                # 8 sample field photos (JPEGs)
├── cache/                     # Cached GEE imagery (auto-populated at runtime)
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── gee_client.py          # GEE Sentinel-2 fetch, NDVI/NDWI computation
│   ├── classifier.py          # CLIP zero-shot photo classification
│   ├── cross_validator.py     # Rule-based photo↔satellite agreement logic
│   ├── health_score.py        # 0-100 watershed health score computation
│   └── map_builder.py         # Folium map with colored pins + popups
├── db/
│   └── watershed.db           # SQLite DB (auto-created at runtime)
└── utils/
    ├── __init__.py
    └── db_utils.py            # SQLite persistence helpers
```

---

### Component 1: Configuration & Dependencies

#### [NEW] [requirements.txt](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/requirements.txt)
```
streamlit>=1.36.0
earthengine-api>=1.1.0
folium>=0.17.0
streamlit-folium>=0.22.0
streamlit-image-comparison>=0.0.4
numpy>=1.26.0
Pillow>=10.0.0
torch>=2.1.0
transformers>=4.40.0
geopandas>=0.14.0
pandas>=2.1.0
requests>=2.31.0
```

#### [NEW] [config.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/config.py)
- GEE collection ID: `COPERNICUS/S2_SR_HARMONIZED`
- Time windows: `T0 = (2024-01-01, 2024-03-31)`, `T_NOW = (2026-06-01, 2026-08-31)`
- Cloud cover threshold: 20%
- Buffer radius: 500m around each point
- Scale: 10m (Sentinel-2 native resolution)
- 5-class labels for CLIP
- Validation rules mapping activity types to expected satellite trends
- Cache directory path

---

### Component 2: Sample Dataset

#### [NEW] [data/sites.csv](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/data/sites.csv)
8 sites in Maharashtra's Ahmednagar/Pune watershed region with realistic coordinates:

| site_id | lat | lon | date | activity_type | photo_filename | notes |
|---------|-----|-----|------|---------------|----------------|-------|
| S01 | 19.095 | 74.738 | 2024-06-15 | check_dam | check_dam_01.jpg | Near Ahmednagar |
| S02 | 19.140 | 74.685 | 2024-07-20 | farm_pond | farm_pond_01.jpg | Irrigation pond |
| S03 | 18.920 | 74.600 | 2024-05-10 | plantation | plantation_01.jpg | Afforestation zone |
| S04 | 19.200 | 74.800 | 2024-08-01 | check_dam | check_dam_02.jpg | Stream crossing |
| S05 | 18.850 | 74.550 | 2024-06-25 | water_body | water_body_01.jpg | Natural reservoir |
| S06 | 19.050 | 74.900 | 2024-07-15 | farm_pond | farm_pond_02.jpg | **ANOMALY** — claims farm pond but location is degraded land |
| S07 | 19.300 | 74.650 | 2024-05-30 | plantation | plantation_02.jpg | Hill slope plantation |
| S08 | 18.980 | 74.750 | 2024-08-10 | degraded_land | degraded_land_01.jpg | Erosion-prone area |

> [!TIP]
> Sites S06 is deliberately designed as an **anomaly** — the photo will show degraded land but the CSV claims it's a farm pond. This creates the "flagged mismatch" demo beat the judges need to see.

#### [NEW] [data/photos/](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/data/photos/)
8 AI-generated field photos matching each site's claimed activity type (except S06, which gets a degraded-land photo despite claiming farm_pond).

---

### Component 3: GEE Client — Sentinel-2 Fetch + NDVI/NDWI

#### [NEW] [src/gee_client.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/src/gee_client.py)

**Key functions:**

- `initialize_gee()` — Authenticate + initialize Earth Engine (handles both service account and interactive auth)
- `fetch_sentinel2_composite(lat, lon, start_date, end_date, buffer_m=500)` → returns median composite as numpy array for bands B2, B3, B4, B8 (Blue, Green, Red, NIR)
- `compute_ndvi(image_array)` → `(B8 - B4) / (B8 + B4)` → mean NDVI float
- `compute_ndwi(image_array)` → `(B3 - B8) / (B3 + B8)` → mean NDWI float
- `get_satellite_thumbnail(lat, lon, start_date, end_date)` → RGB thumbnail PNG for visual display
- `get_indices_for_site(lat, lon, config)` → returns dict `{ndvi_t0, ndvi_tnow, ndwi_t0, ndwi_tnow, delta_ndvi, delta_ndwi, thumb_t0, thumb_tnow}`

**Caching strategy:**
- After first GEE fetch, save results as JSON + PNG thumbnails in `cache/{site_id}/`
- On subsequent runs, load from cache — **no live GEE calls if cache exists**
- This handles the "bad wifi at demo" constraint

---

### Component 4: Photo Classifier (CLIP Zero-Shot)

#### [NEW] [src/classifier.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/src/classifier.py)

**Key functions:**

- `load_clip_model()` → loads `openai/clip-vit-base-patch32` (smallest CLIP, fast inference)
- `classify_photo(image_path, labels)` → returns `{predicted_class, confidence, all_scores}`

**CLIP prompt engineering (critical for accuracy):**
```python
LABELS = [
    "a photograph of a check dam across a stream",
    "a photograph of a farm pond for water harvesting",
    "a photograph of a tree plantation or afforestation area",
    "a photograph of degraded barren land with erosion",
    "a photograph of a water body like a lake or reservoir"
]
CLASS_MAP = {0: "check_dam", 1: "farm_pond", 2: "plantation", 3: "degraded_land", 4: "water_body"}
```

**Caching:** Model loaded once in `st.session_state`, classification results cached per photo hash.

---

### Component 5: Cross-Validation Logic

#### [NEW] [src/cross_validator.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/src/cross_validator.py)

**Rule-based validation matrix:**

| Claimed Activity | Expected NDVI Trend | Expected NDWI Trend | Photo Should Match |
|-----------------|--------------------|--------------------|-------------------|
| check_dam | stable/increase | increase | check_dam |
| farm_pond | stable | increase | farm_pond |
| plantation | increase (>0.05) | stable | plantation |
| water_body | stable/decrease | high (>0.0) | water_body |
| degraded_land | low (<0.2) | low (<-0.1) | degraded_land |

**Validation output per site:**
```python
{
    "satellite_agreement": True/False,  # Does NDVI/NDWI trend match expected?
    "photo_agreement": True/False,       # Does CLIP class match claimed type?
    "overall_status": "confirmed" | "anomaly" | "inconclusive",
    "flags": ["NDWI decrease contradicts farm_pond claim", ...],
    "confidence": 0.0-1.0
}
```

**Status logic:**
- **confirmed** (green): both satellite AND photo agree with claim
- **anomaly** (red): either satellite OR photo disagrees
- **inconclusive** (yellow): satellite data ambiguous (cloud cover, low confidence)

---

### Component 6: Health Score

#### [NEW] [src/health_score.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/src/health_score.py)

**Formula (0-100 per site):**

```
health_score = (
    0.30 × ndvi_score +      # NDVI trend component (0-100)
    0.30 × ndwi_score +      # NDWI trend component (0-100)
    0.25 × agreement_score + # Photo-satellite agreement (0 or 100)
    0.15 × confidence_score  # Classifier confidence (0-100)
)
```

Where:
- `ndvi_score` = normalize `delta_ndvi` from [-0.3, +0.3] → [0, 100]
- `ndwi_score` = normalize `delta_ndwi` from [-0.3, +0.3] → [0, 100]
- `agreement_score` = 100 if `overall_status == "confirmed"`, 50 if inconclusive, 0 if anomaly
- `confidence_score` = CLIP confidence × 100

---

### Component 7: Folium Map Builder

#### [NEW] [src/map_builder.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/src/map_builder.py)

- `build_map(sites_df, validation_results)` → returns `folium.Map`
- Pins colored by status: 🟢 green = confirmed, 🔴 red = anomaly, 🟡 orange = inconclusive
- Each pin tooltip shows: site_id, activity_type, health_score
- Each pin popup shows: mini summary of validation result
- Map centered on mean of all coordinates, auto-zoom to fit all points

---

### Component 8: SQLite Persistence

#### [NEW] [utils/db_utils.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/utils/db_utils.py)

- `init_db()` → creates `sites` and `analysis_results` tables
- `save_analysis(site_id, results_dict)` → persist computed indices + validation
- `load_analysis(site_id)` → retrieve cached analysis
- `get_all_results()` → for dashboard summary

---

### Component 9: Streamlit App (Main UI)

#### [NEW] [app.py](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/app.py)

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  🌊 Watershed Photo-Satellite Fusion Dashboard          │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │           Interactive Folium Map                 │    │
│  │     (colored pins, click to select site)        │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  Summary Bar: [8 sites] [5 confirmed] [1 anomaly]       │
│               [2 inconclusive] [Avg Health: 72]         │
│                                                         │
│  ═══════════════════════════════════════════════════════ │
│  Selected Site: S06 — Farm Pond (ANOMALY 🔴)            │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  ┌──────────────┐  ┌──────────────────────────────┐     │
│  │              │  │   Before / After Satellite    │     │
│  │  Field Photo │  │     ◄══════|══════►          │     │
│  │  (from JPEG) │  │   (image comparison slider)  │     │
│  │              │  │                              │     │
│  └──────────────┘  └──────────────────────────────┘     │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Health Score: ██████████░░░░░ 42/100             │  │
│  │  NDVI: 0.15 → 0.12 (▼ -0.03)                     │  │
│  │  NDWI: -0.20 → -0.25 (▼ -0.05)                   │  │
│  │  Photo Class: degraded_land (89% conf)            │  │
│  │  Claimed: farm_pond                               │  │
│  │  ⚠ FLAGS:                                         │  │
│  │    • NDWI decrease contradicts farm_pond claim    │  │
│  │    • Photo shows degraded_land, not farm_pond     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Streamlit features used:**
- `st.set_page_config(layout="wide")` for full-width
- `st_folium()` for interactive map with click detection
- `streamlit-image-comparison` for before/after satellite slider
- `st.columns()` for side-by-side photo + satellite layout
- `st.metric()` for NDVI/NDWI delta display
- `st.progress()` for health score bar
- `st.session_state` for selected site persistence
- Custom CSS for dark theme + styled anomaly cards

---

### Component 10: README

#### [MODIFY] [README.md](file:///d:/projects/git%20demo/Clean-water-Initiative/Clean-water-Initiative/README.md)
Complete rewrite with:
- Project overview + SIH context
- Screenshots placeholder
- Setup instructions (< 10 min from fresh clone)
- `pip install -r requirements.txt`
- `earthengine authenticate` instructions
- `streamlit run app.py`
- Architecture diagram (mermaid)
- Demo walkthrough

---

## Verification Plan

### Automated Tests
```bash
# 1. Verify all imports resolve
python -c "from src.gee_client import *; from src.classifier import *; from src.cross_validator import *"

# 2. Verify CLIP classifier works on sample photos
python -c "from src.classifier import load_clip_model, classify_photo; m,p = load_clip_model(); print(classify_photo('data/photos/check_dam_01.jpg', m, p))"

# 3. Verify Streamlit app launches without errors
streamlit run app.py --server.headless true
```

### Manual Verification
1. Open Streamlit app in browser → map loads with 8 colored pins
2. Click S06 (the anomaly site) → see red anomaly flag with explanation
3. Verify before/after satellite slider works
4. Confirm health scores are in 0-100 range and make directional sense
5. Verify the app works fully from cache (disconnect wifi, reload)

---

## Build Order (Matches Your Spec)

| Step | What | Depends On |
|------|------|------------|
| 1 | Sample dataset (CSV + generated photos) | Nothing |
| 2 | `config.py` + `requirements.txt` | Nothing |
| 3 | `src/gee_client.py` + verify one coordinate fetch | Step 2 |
| 4 | NDVI/NDWI calculation + verify values | Step 3 |
| 5 | `src/classifier.py` + run on sample photos | Step 1, 2 |
| 6 | `src/cross_validator.py` + `src/health_score.py` | Step 4, 5 |
| 7 | `src/map_builder.py` + `utils/db_utils.py` | Step 6 |
| 8 | `app.py` — full Streamlit dashboard | All above |
| 9 | Polish: dark theme CSS, README, cache pre-population | Step 8 |
