import { Site, AnalysisResult, Photo, SystemHealth, AdHocAnalysisPayload } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Clean initial state — no hardcoded preset sites
export const FALLBACK_DEMO_SITES: Site[] = [];

export async function fetchHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) throw new Error("Health check failed");
    return await res.json();
  } catch {
    return {
      status: "offline",
      services: {
        gee_configured: false,
        clip_model_loaded: false,
        storage_configured: false,
      },
    };
  }
}

export async function fetchSites(seededOnly: boolean = false): Promise<Site[]> {
  try {
    const res = await fetch(`${API_BASE}/sites?seeded_only=${seededOnly}&limit=100`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to fetch sites");
    const data = await res.json();
    return data.sites || [];
  } catch (err) {
    console.warn("Using fallback demo sites (backend offline):", err);
    return FALLBACK_DEMO_SITES;
  }
}

export async function fetchSite(siteId: string): Promise<Site | null> {
  try {
    const res = await fetch(`${API_BASE}/sites/${siteId}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch site");
    return await res.json();
  } catch {
    return FALLBACK_DEMO_SITES.find((s) => s.id === siteId) || null;
  }
}

export async function createSite(payload: Partial<Site>): Promise<Site> {
  const res = await fetch(`${API_BASE}/sites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to create site" }));
    throw new Error(err.detail || "Failed to create site");
  }
  return await res.json();
}

export async function runAdHocAnalysis(payload: AdHocAnalysisPayload): Promise<AnalysisResult> {
  try {
    const res = await fetch(`${API_BASE}/analysis/adhoc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
      throw new Error(err.detail || "Analysis failed");
    }
    const raw = await res.json();

    // Normalize backend nested structure to flat frontend AnalysisResult interface
    const sat = raw.satellite || {};
    const hs = raw.health_score || {};
    const cv = raw.cross_validation || {};

    const deltaNdvi =
      typeof sat.delta_ndvi === "number"
        ? sat.delta_ndvi
        : typeof raw.delta_ndvi === "number"
        ? raw.delta_ndvi
        : null;

    const deltaNdwi =
      typeof sat.delta_ndwi === "number"
        ? sat.delta_ndwi
        : typeof raw.delta_ndwi === "number"
        ? raw.delta_ndwi
        : null;

    const ndviT0 =
      typeof sat.ndvi_t0 === "number"
        ? sat.ndvi_t0
        : typeof raw.ndvi_t0 === "number"
        ? raw.ndvi_t0
        : null;

    const ndviTnow =
      typeof sat.ndvi_tnow === "number"
        ? sat.ndvi_tnow
        : typeof raw.ndvi_tnow === "number"
        ? raw.ndvi_tnow
        : null;

    const ndwiT0 =
      typeof sat.ndwi_t0 === "number"
        ? sat.ndwi_t0
        : typeof raw.ndwi_t0 === "number"
        ? raw.ndwi_t0
        : null;

    const ndwiTnow =
      typeof sat.ndwi_tnow === "number"
        ? sat.ndwi_tnow
        : typeof raw.ndwi_tnow === "number"
        ? raw.ndwi_tnow
        : null;

    const score =
      typeof hs.score === "number"
        ? hs.score
        : typeof raw.health_score === "number"
        ? raw.health_score
        : null;

    const grade =
      typeof hs.grade === "string"
        ? hs.grade
        : typeof raw.health_grade === "string"
        ? raw.health_grade
        : null;

    const status = cv.overall_status || raw.overall_status || "inconclusive";

    return {
      id: raw.id || "adhoc-" + Date.now(),
      site_id: raw.site_id || "adhoc-site",
      mode: raw.mode || (payload.baseline_date ? "full" : "snapshot"),
      health_score: score,
      health_grade: grade,
      delta_ndvi: deltaNdvi !== null ? Number(deltaNdvi.toFixed(4)) : null,
      delta_ndwi: deltaNdwi !== null ? Number(deltaNdwi.toFixed(4)) : null,
      ndvi_t0: ndviT0 !== null ? Number(ndviT0.toFixed(4)) : null,
      ndvi_tnow: ndviTnow !== null ? Number(ndviTnow.toFixed(4)) : null,
      ndwi_t0: ndwiT0 !== null ? Number(ndwiT0.toFixed(4)) : null,
      ndwi_tnow: ndwiTnow !== null ? Number(ndwiTnow.toFixed(4)) : null,
      satellite_agreement: cv.satellite_agreement ?? null,
      photo_agreement: cv.photo_agreement ?? null,
      overall_status: status,
      flags: cv.flags || raw.flags || [],
      confidence_score: cv.confidence ?? null,
      classified_activity: payload.claimed_activity_type || null,
      classification_confidence: null,
      satellite_source: sat.source || raw.satellite_source || "gee",
      buffer_radius_m: raw.buffer_radius_m || payload.buffer_radius_m || 500,
      analyzed_at: raw.created_at || new Date().toISOString(),
    };
  } catch (err) {
    const isDemo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
    if (!isDemo) {
      // Re-throw so caller displays explicit error state
      throw err;
    }
    // Gated fallback: only when NEXT_PUBLIC_DEMO_MODE is true, carrying source="simulated"
    console.warn("NEXT_PUBLIC_DEMO_MODE active: using simulated preview:", err);
    return {
      id: "adhoc-" + Date.now(),
      site_id: "adhoc-site",
      mode: payload.baseline_date ? "full" : "snapshot",
      health_score: 72,
      health_grade: "B",
      delta_ndvi: payload.baseline_date ? 0.10 : null,
      delta_ndwi: payload.baseline_date ? 0.05 : null,
      ndvi_t0: payload.baseline_date ? 0.22 : null,
      ndvi_tnow: 0.32,
      ndwi_t0: payload.baseline_date ? -0.15 : null,
      ndwi_tnow: -0.10,
      satellite_agreement: true,
      photo_agreement: null,
      overall_status: "confirmed",
      flags: [],
      confidence_score: 0.85,
      classified_activity: payload.claimed_activity_type || null,
      classification_confidence: 0.85,
      satellite_source: "simulated",
      buffer_radius_m: payload.buffer_radius_m || 500,
      analyzed_at: new Date().toISOString(),
    };
  }
}

export function normalizePhoto(raw: any): Photo {
  const exif = raw.exif || {};
  const classification = raw.classification || {};

  const hasGps =
    typeof raw.exif_has_gps === "boolean"
      ? raw.exif_has_gps
      : typeof exif.has_gps === "boolean"
      ? exif.has_gps
      : false;

  const exifLat =
    typeof raw.exif_lat === "number"
      ? raw.exif_lat
      : typeof exif.gps_lat === "number"
      ? exif.gps_lat
      : null;

  const exifLon =
    typeof raw.exif_lon === "number"
      ? raw.exif_lon
      : typeof exif.gps_lon === "number"
      ? exif.gps_lon
      : null;

  const exifCamera =
    raw.exif_camera ||
    exif.camera_model ||
    null;

  const exifTimestamp =
    raw.exif_timestamp ||
    exif.capture_datetime ||
    null;

  const predictedClass =
    raw.predicted_class ||
    classification.predicted_class ||
    null;

  const confidence =
    typeof raw.classification_confidence === "number"
      ? raw.classification_confidence
      : typeof classification.confidence === "number"
      ? classification.confidence
      : null;

  const allScores =
    raw.all_scores ||
    classification.all_scores ||
    (raw.classification_scores_json ? JSON.parse(raw.classification_scores_json) : null);

  const warnings =
    Array.isArray(raw.exif_warnings)
      ? raw.exif_warnings
      : Array.isArray(exif.warnings)
      ? exif.warnings
      : [];

  return {
    id: raw.id,
    site_id: raw.site_id,
    file_path: raw.file_path || raw.storage_path || "",
    public_url: raw.public_url || null,
    file_size_bytes: raw.file_size_bytes ?? null,
    mime_type: raw.mime_type || raw.content_type || "image/jpeg",
    original_filename: raw.original_filename || "photo.jpg",
    predicted_class: predictedClass,
    classification_confidence: confidence,
    all_scores: allScores,
    all_scores_json: raw.all_scores_json,
    exif_camera: exifCamera,
    exif_timestamp: exifTimestamp,
    exif_lat: exifLat,
    exif_lon: exifLon,
    exif_has_gps: hasGps,
    exif_warnings: warnings,
    exif_warnings_json: raw.exif_warnings_json,
    created_at: raw.created_at || new Date().toISOString(),
  };
}

export async function uploadSitePhoto(
  siteId: string,
  file: File,
  clientCoords?: { lat: number; lon: number }
): Promise<Photo> {
  const formData = new FormData();
  formData.append("file", file);
  if (clientCoords && typeof clientCoords.lat === "number" && typeof clientCoords.lon === "number") {
    formData.append("client_lat", String(clientCoords.lat));
    formData.append("client_lon", String(clientCoords.lon));
  }

  const res = await fetch(`${API_BASE}/photos/${siteId}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  const raw = await res.json();
  return normalizePhoto(raw);
}

export async function updatePhotoGeotag(
  photoId: string,
  lat: number,
  lon: number
): Promise<Photo> {
  const formData = new FormData();
  formData.append("lat", String(lat));
  formData.append("lon", String(lon));

  const res = await fetch(`${API_BASE}/photos/${photoId}/geotag`, {
    method: "PATCH",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Geotag update failed" }));
    throw new Error(err.detail || "Geotag update failed");
  }
  const raw = await res.json();
  return normalizePhoto(raw);
}

export async function fetchSitePhotos(siteId: string): Promise<Photo[]> {
  try {
    const res = await fetch(`${API_BASE}/photos/${siteId}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch photos");
    const data = await res.json();
    const list = Array.isArray(data) ? data : (data.photos || []);
    return list.map(normalizePhoto);
  } catch {
    return [];
  }
}

export function getReportDownloadUrl(siteId: string): string {
  return `${API_BASE}/reports/${siteId}/pdf`;
}

export interface AutoAuditResult {
  site: Site;
  photo: Photo;
  analysis: AnalysisResult;
  cross_validation: {
    satellite_agreement: boolean | null;
    photo_agreement: boolean | null;
    overall_status: "confirmed" | "anomaly" | "inconclusive";
    flags: string[];
    confidence: number;
  };
  health_score: {
    score: number;
    grade: string;
    mode: string;
    components: Record<string, number>;
  };
  satellite_data: any;
  report_download_url: string;
}

export async function auditPhotoAuto(
  file: File,
  options?: {
    claimed_activity_type?: string;
    clientCoords?: { lat: number; lon: number };
    siteId?: string;
    siteName?: string;
    bufferRadiusM?: number;
  }
): Promise<AutoAuditResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.claimed_activity_type) {
    formData.append("claimed_activity_type", options.claimed_activity_type);
  }
  if (options?.clientCoords) {
    formData.append("client_lat", String(options.clientCoords.lat));
    formData.append("client_lon", String(options.clientCoords.lon));
  }
  if (options?.siteId) {
    formData.append("site_id", options.siteId);
  }
  if (options?.siteName) {
    formData.append("site_name", options.siteName);
  }
  if (options?.bufferRadiusM) {
    formData.append("buffer_radius_m", String(options.bufferRadiusM));
  }

  const res = await fetch(`${API_BASE}/photos/auto-audit`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Auto-audit failed" }));
    throw new Error(err.detail || "Auto-audit failed");
  }

  const data = await res.json();
  return {
    ...data,
    photo: normalizePhoto(data.photo),
    site: data.site,
    analysis: data.analysis,
  };
}

export interface GeocodeResult {
  name: string;
  displayName: string;
  lat: number;
  lon: number;
  type?: string;
}

export async function geocodeQuery(q: string, limit: number = 6): Promise<GeocodeResult[]> {
  try {
    const res = await fetch(`${API_BASE}/geocode?q=${encodeURIComponent(q)}&limit=${limit}`);
    if (!res.ok) throw new Error("Geocode search failed");
    return await res.json();
  } catch (err) {
    console.warn("Backend geocode search failed, falling back:", err);
    return [];
  }
}

export async function reverseGeocode(lat: number, lon: number): Promise<GeocodeResult> {
  try {
    const res = await fetch(`${API_BASE}/geocode/reverse?lat=${lat}&lon=${lon}`);
    if (!res.ok) throw new Error("Reverse geocode failed");
    return await res.json();
  } catch (err) {
    console.warn("Backend reverse geocode failed:", err);
    return {
      name: `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`,
      displayName: `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
      lat,
      lon,
      type: "coordinate",
    };
  }
}

