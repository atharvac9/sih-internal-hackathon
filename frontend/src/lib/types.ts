export type ActivityType =
  | "check_dam"
  | "farm_pond"
  | "plantation"
  | "contour_trench"
  | "desilting"
  | "gabion"
  | "percolation_tank"
  | "loose_boulder";

export type OverallStatus = "confirmed" | "anomaly" | "inconclusive";

export interface Site {
  id: string;
  site_code?: string | null;
  lat: number;
  lon: number;
  activity_type: ActivityType | string | null;
  description: string | null;
  baseline_date: string | null;
  intervention_date: string | null;
  buffer_radius_m: number;
  is_seeded_demo: boolean;
  created_at: string;
  updated_at: string;
  latest_analysis?: AnalysisResult | null;
  photo_count?: number;
}

export interface AnalysisResult {
  id: string;
  site_id: string;
  mode: "full" | "snapshot";
  health_score: number | null;
  health_grade: "A" | "B" | "C" | "D" | "F" | string | null;
  delta_ndvi: number | null;
  delta_ndwi: number | null;
  ndvi_t0: number | null;
  ndvi_tnow: number | null;
  ndwi_t0: number | null;
  ndwi_tnow: number | null;
  satellite_agreement: boolean | null;
  photo_agreement: boolean | null;
  overall_status: OverallStatus | null;
  flags: string[];
  flags_json?: string;
  confidence_score: number | null;
  classified_activity: string | null;
  classification_confidence: number | null;
  satellite_source: string;
  buffer_radius_m: number;
  analyzed_at: string;
}

export interface Photo {
  id: string;
  site_id: string;
  file_path: string;
  public_url: string | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  original_filename: string | null;
  predicted_class: string | null;
  classification_confidence: number | null;
  all_scores: Record<string, number> | null;
  all_scores_json?: string;
  exif_camera: string | null;
  exif_timestamp: string | null;
  exif_lat: number | null;
  exif_lon: number | null;
  exif_has_gps: boolean;
  exif_warnings: string[];
  exif_warnings_json?: string;
  created_at: string;
}

export interface SystemHealth {
  status: string;
  services: {
    gee_configured: boolean;
    clip_model_loaded: boolean;
    storage_configured: boolean;
  };
}

export interface AdHocAnalysisPayload {
  lat: number;
  lon: number;
  claimed_activity_type?: string | null;
  buffer_radius_m?: number;
  baseline_date?: string | null;
}
