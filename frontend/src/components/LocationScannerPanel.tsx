"use client";

import React, { useState, useEffect, useRef } from "react";
import { Site, ActivityType, AnalysisResult, Photo } from "../lib/types";
import { LocationSearchInput, GeocodedLocation } from "./LocationSearchInput";
import { ReportModal } from "./ReportModal";
import { SiteInspector } from "./SiteInspector";
import { runAdHocAnalysis, createSite, auditPhotoAuto, AutoAuditResult, getReportDownloadUrl } from "../lib/api";
import {
  Sparkles,
  MapPin,
  Check,
  AlertCircle,
  ArrowRight,
  Loader2,
  FileDown,
  Layers,
  ChevronRight,
  ShieldCheck,
  Compass,
  X,
  Sliders,
  CheckCircle2,
  Camera,
  Upload,
  AlertTriangle,
  Eye,
  RefreshCw,
  FileText,
} from "lucide-react";

interface LocationScannerPanelProps {
  selectedSite: Site | null;
  activeLocation: GeocodedLocation | null;
  onLocationSelect: (location: GeocodedLocation) => void;
  onClearLocation: () => void;
  onSiteSaved: (site: Site) => void;
  onUploadPhotoClick: (site: Site) => void;
  onClearSelectedSite: () => void;
}

export const LocationScannerPanel: React.FC<LocationScannerPanelProps> = ({
  selectedSite,
  activeLocation,
  onLocationSelect,
  onClearLocation,
  onSiteSaved,
  onUploadPhotoClick,
  onClearSelectedSite,
}) => {
  // Panel mode: "photo_audit" (default 1-click sync) or "manual_scan"
  const [panelMode, setPanelMode] = useState<"photo_audit" | "manual_scan">("photo_audit");

  // Coordinates from activeLocation (or default fallback)
  const lat = activeLocation?.lat ?? 19.085;
  const lon = activeLocation?.lon ?? 74.75;
  const locationName = activeLocation?.name ?? "Selected Map Location";

  // Scanner configuration
  const [activityType, setActivityType] = useState<ActivityType>("check_dam");
  const [bufferRadius, setBufferRadius] = useState<number>(500);
  const [hasBaseline, setHasBaseline] = useState<boolean>(true);
  const [baselineDate, setBaselineDate] = useState<string>("2023-01-15");

  // Manual Analysis & Saved Site states
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [savedSite, setSavedSite] = useState<Site | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 1-Click Photo Auto-Audit states
  const [selectedPhotoFile, setSelectedPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [auditStep, setAuditStep] = useState<number>(0);
  const [autoAuditResult, setAutoAuditResult] = useState<AutoAuditResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // PDF Report modal state
  const [reportModalOpen, setReportModalOpen] = useState<boolean>(false);

  // Reset manual analysis results when active location changes
  useEffect(() => {
    setAnalysisResult(null);
    setSavedSite(null);
    setError(null);
  }, [activeLocation?.lat, activeLocation?.lon]);

  // Execute Manual Telemetry Scan
  const handleExecuteScan = async () => {
    setIsScanning(true);
    setError(null);
    try {
      const data = await runAdHocAnalysis({
        lat,
        lon,
        claimed_activity_type: activityType,
        baseline_date: hasBaseline ? baselineDate : undefined,
        buffer_radius_m: bufferRadius,
      });
      setAnalysisResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to execute telemetry analysis");
    } finally {
      setIsScanning(false);
    }
  };

  // Save manual scan as Monitored Site
  const handleSaveSite = async () => {
    try {
      const newSite = await createSite({
        lat,
        lon,
        activity_type: activityType,
        buffer_radius_m: bufferRadius,
        baseline_date: hasBaseline ? baselineDate : undefined,
        description: `Monitored ${activityType.replace(/_/g, " ")} at ${locationName} (${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E)`,
      });
      newSite.latest_analysis = analysisResult;
      setSavedSite(newSite);
      onSiteSaved(newSite);
    } catch (err: any) {
      setError(err.message || "Failed to save monitored site");
    }
  };

  // Photo Selection handler
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setSelectedPhotoFile(f);
      setPhotoPreviewUrl(URL.createObjectURL(f));
      setAutoAuditResult(null);
      setError(null);
    }
  };

  // Photo Drop handler
  const handlePhotoDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      setSelectedPhotoFile(f);
      setPhotoPreviewUrl(URL.createObjectURL(f));
      setAutoAuditResult(null);
      setError(null);
    }
  };

  // Execute Unified 1-Click Photo Auto-Audit
  const handleExecutePhotoAudit = async () => {
    if (!selectedPhotoFile) return;
    setIsAuditing(true);
    setError(null);
    setAuditStep(1);

    try {
      // Step 1 -> 2: Upload, parse EXIF, run computer vision, pull satellite telemetry
      const res = await auditPhotoAuto(selectedPhotoFile, {
        claimed_activity_type: activityType,
        bufferRadiusM: bufferRadius,
        clientCoords: activeLocation ? { lat: activeLocation.lat, lon: activeLocation.lon } : undefined,
      });

      setAuditStep(4);
      setAutoAuditResult(res);
      setSavedSite(res.site);
      onSiteSaved(res.site);

      // Automatically sync map to the photo's GPS coordinates!
      onLocationSelect({
        name: res.site.description || `Photo Audit Point (${res.site.lat.toFixed(4)}, ${res.site.lon.toFixed(4)})`,
        displayName: `${res.site.lat.toFixed(4)}°N, ${res.site.lon.toFixed(4)}°E`,
        lat: res.site.lat,
        lon: res.site.lon,
      });

    } catch (err: any) {
      console.error("Auto-audit failure:", err);
      setError(err.message || "Failed to run automated photo-to-satellite audit. Check photo GPS metadata.");
    } finally {
      setIsAuditing(false);
    }
  };

  // If user selected an existing monitored site, show SiteInspector with a search bar on top
  if (selectedSite) {
    return (
      <div className="flex flex-col gap-4">
        {/* Search Bar on top so user can search anytime */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-xs flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-teal-600" />
              <span>Search Another Location</span>
            </span>
            <button
              onClick={onClearSelectedSite}
              className="text-xs font-medium text-teal-700 hover:text-teal-900 cursor-pointer"
            >
              Back to Scanner
            </button>
          </div>
          <LocationSearchInput
            onLocationSelect={onLocationSelect}
            initialQuery={activeLocation?.name || ""}
          />
        </div>

        {/* Existing Site Inspector */}
        <SiteInspector
          site={selectedSite}
          onUploadPhotoClick={onUploadPhotoClick}
          onClose={onClearSelectedSite}
        />
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs flex flex-col gap-5 text-slate-800">
        {/* Mode Switcher Tabs */}
        <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200/80">
          <button
            onClick={() => {
              setPanelMode("photo_audit");
              setError(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              panelMode === "photo_audit"
                ? "bg-white text-teal-800 shadow-xs border border-slate-200/60"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Camera className="w-3.5 h-3.5 text-teal-600" />
            <span>Photo Auto-Audit</span>
            <span className="text-[10px] font-mono bg-teal-50 text-teal-700 border border-teal-200 px-1.5 py-0.2 rounded-full hidden sm:inline">
              1-Click Sync
            </span>
          </button>

          <button
            onClick={() => {
              setPanelMode("manual_scan");
              setError(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              panelMode === "manual_scan"
                ? "bg-white text-teal-800 shadow-xs border border-slate-200/60"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Compass className="w-3.5 h-3.5 text-slate-500" />
            <span>Coordinate Scanner</span>
          </button>
        </div>

        {/* ── MODE 1: UNIFIED 1-CLICK PHOTO AUTO-AUDIT ─────────────────────── */}
        {panelMode === "photo_audit" ? (
          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>Unified Field Photo & Satellite Audit</span>
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Upload a geotagged photo. NeerDrishti automatically extracts coordinates, syncs Sentinel-2 satellite telemetry, cross-validates evidence, and compiles the report.
              </p>
            </div>

            {/* Photo Dropzone / Selector */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handlePhotoDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-4 flex flex-col items-center justify-center gap-2.5 transition-all cursor-pointer ${
                selectedPhotoFile
                  ? "border-teal-400 bg-teal-50/40"
                  : "border-slate-300 hover:border-teal-500 hover:bg-slate-50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handlePhotoSelect}
                className="hidden"
              />

              {photoPreviewUrl ? (
                <div className="flex items-center gap-3.5 w-full">
                  <img
                    src={photoPreviewUrl}
                    alt="Uploaded preview"
                    className="w-16 h-16 rounded-xl object-cover border border-teal-200 shadow-xs shrink-0"
                  />
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="text-xs font-bold text-slate-900 truncate">
                      {selectedPhotoFile?.name}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      {((selectedPhotoFile?.size || 0) / 1024).toFixed(1)} KB
                    </span>
                    <span className="text-[10px] text-teal-700 font-semibold mt-1 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Ready for Satellite Sync</span>
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="text-[11px] text-teal-700 hover:text-teal-900 font-semibold px-2.5 py-1 bg-white border border-teal-200 rounded-lg shadow-2xs hover:bg-teal-50 shrink-0"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <>
                  <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600 shadow-2xs">
                    <Upload className="w-5 h-5" />
                  </div>
                  <div className="text-center">
                    <span className="text-xs font-bold text-slate-800">
                      Drop Geotagged Field Photo Here
                    </span>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      JPEG, PNG or WebP with camera GPS metadata
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Claimed Intervention Configuration */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Claimed Intervention Activity
              </label>
              <select
                value={activityType}
                onChange={(e) => setActivityType(e.target.value as ActivityType)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white capitalize transition-all cursor-pointer"
              >
                <option value="check_dam">Check Dam (Nala Bund)</option>
                <option value="farm_pond">Farm Pond / Reservoir</option>
                <option value="plantation">Afforestation / Tree Plantation</option>
                <option value="contour_trench">Contour Trenching (CCT)</option>
                <option value="desilting">Waterbody Desilting</option>
                <option value="percolation_tank">Percolation Tank</option>
                <option value="water_body">Natural Water Body</option>
              </select>
            </div>

            {/* Error Message Banner */}
            {error && (
              <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl flex items-start gap-2.5 text-xs text-rose-800">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div className="flex flex-col gap-1">
                  <span className="font-semibold">Audit Warning</span>
                  <span>{error}</span>
                </div>
              </div>
            )}

            {/* Audit CTA Button */}
            <button
              onClick={handleExecutePhotoAudit}
              disabled={!selectedPhotoFile || isAuditing}
              className="flex items-center justify-center gap-2 w-full py-3.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-md shadow-teal-700/20 transition-all cursor-pointer disabled:opacity-40 active:scale-[0.99]"
            >
              {isAuditing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Syncing Satellite Telemetry & Auditing Evidence...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Sync Coordinates & Run Full Audit</span>
                </>
              )}
            </button>

            {/* ── AUTO AUDIT RESULTS CARD ──────────────────────────────────── */}
            {autoAuditResult && (
              <div className="flex flex-col gap-4 pt-2 border-t border-slate-100 animate-in fade-in duration-300">
                {/* Status Badge */}
                <div
                  className={`p-3.5 rounded-xl border flex items-center justify-between ${
                    autoAuditResult.cross_validation.overall_status === "confirmed"
                      ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                      : autoAuditResult.cross_validation.overall_status === "anomaly"
                      ? "bg-rose-50 border-rose-200 text-rose-900"
                      : "bg-amber-50 border-amber-200 text-amber-900"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {autoAuditResult.cross_validation.overall_status === "confirmed" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
                    )}
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider">
                        {autoAuditResult.cross_validation.overall_status === "confirmed"
                          ? "Intervention Confirmed"
                          : autoAuditResult.cross_validation.overall_status === "anomaly"
                          ? "Cross-Validation Anomaly Flagged"
                          : "Audit Inconclusive"}
                      </div>
                      <div className="text-[11px] opacity-80 mt-0.5">
                        Site: {autoAuditResult.site.site_code || autoAuditResult.site.id.substring(0, 8)} •{" "}
                        {autoAuditResult.site.lat.toFixed(4)}°N, {autoAuditResult.site.lon.toFixed(4)}°E
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-lg font-black font-mono">
                      {autoAuditResult.health_score.score}
                    </span>
                    <span className="text-xs font-bold font-mono ml-1 px-1.5 py-0.5 rounded bg-white/80 border">
                      Grade {autoAuditResult.health_score.grade}
                    </span>
                  </div>
                </div>

                {/* Side-by-Side Comparison: Photo vs Satellite */}
                <div className="grid grid-cols-2 gap-2.5 text-xs">
                  {/* Photo Evidence */}
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex flex-col gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Ground Photo AI
                    </span>
                    <div className="font-bold text-slate-900 capitalize text-xs">
                      {autoAuditResult.photo.predicted_class?.replace(/_/g, " ") || "Unknown"}
                    </div>
                    <div className="text-[11px] font-mono text-teal-700 font-semibold">
                      {((autoAuditResult.photo.classification_confidence || 0) * 100).toFixed(1)}% certainty
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-1 truncate">
                      📍 {autoAuditResult.photo.exif_lat?.toFixed(4)}°, {autoAuditResult.photo.exif_lon?.toFixed(4)}°
                    </div>
                  </div>

                  {/* Satellite Telemetry */}
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex flex-col gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                      Sentinel-2 Satellite
                    </span>
                    <div className="flex items-center justify-between font-mono">
                      <span className="text-slate-600">NDVI:</span>
                      <span className="font-bold text-emerald-700">
                        {autoAuditResult.satellite_data.ndvi_tnow?.toFixed(3) || "N/A"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between font-mono">
                      <span className="text-slate-600">NDWI:</span>
                      <span className="font-bold text-sky-700">
                        {autoAuditResult.satellite_data.ndwi_tnow?.toFixed(3) || "N/A"}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-1">
                      Buffer: {autoAuditResult.site.buffer_radius_m}m
                    </div>
                  </div>
                </div>

                {/* Flags list */}
                {autoAuditResult.cross_validation.flags && autoAuditResult.cross_validation.flags.length > 0 && (
                  <div className="bg-rose-50/70 p-3 rounded-xl border border-rose-200/80 flex flex-col gap-1 text-xs">
                    <span className="font-bold text-rose-800 text-[11px]">Audit Diagnostic Flags:</span>
                    <ul className="list-disc list-inside text-rose-700 space-y-0.5 text-[11px]">
                      {autoAuditResult.cross_validation.flags.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Buttons: View Report & Download PDF */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setReportModalOpen(true)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-xs transition-all cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>View Audit Report</span>
                  </button>

                  <a
                    href={getReportDownloadUrl(autoAuditResult.site.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs border border-slate-200 transition-all cursor-pointer"
                  >
                    <FileDown className="w-3.5 h-3.5" />
                    <span>Download PDF</span>
                  </a>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ── MODE 2: MANUAL LOCATION SEARCH & COORDINATES SCANNER ─────────── */
          <div className="flex flex-col gap-4">
            {/* 1. Location Search Input */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-slate-700 flex items-center justify-between">
                <span>1. Search Preferred Location</span>
                <span className="text-[10px] font-normal text-teal-700 bg-teal-50 px-2 py-0.5 rounded-md border border-teal-200">
                  City, Village, River
                </span>
              </label>
              <LocationSearchInput
                onLocationSelect={onLocationSelect}
                initialQuery={activeLocation?.name || ""}
                placeholder="Type city, village, river (e.g. Pune, Godavari)..."
              />
            </div>

            {/* 2. System-Fetched Coordinates Card */}
            <div className="bg-slate-50/80 rounded-xl p-3.5 border border-slate-200 flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <MapPin className="w-3.5 h-3.5 text-teal-600" />
                  <span className="truncate max-w-[200px]">
                    {activeLocation ? activeLocation.name : "Target Map Coordinates"}
                  </span>
                </div>
                <span className="text-[10px] font-medium font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200 flex items-center gap-1">
                  <Check className="w-3 h-3" />
                  <span>System Fetched</span>
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                <div className="bg-white px-3 py-2 rounded-lg border border-slate-200/80 flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-sans font-semibold">
                    Latitude (°N)
                  </span>
                  <span className="font-bold text-slate-900 mt-0.5">{lat.toFixed(4)}°N</span>
                </div>
                <div className="bg-white px-3 py-2 rounded-lg border border-slate-200/80 flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase font-sans font-semibold">
                    Longitude (°E)
                  </span>
                  <span className="font-bold text-slate-900 mt-0.5">{lon.toFixed(4)}°E</span>
                </div>
              </div>

              {activeLocation?.displayName && (
                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                  {activeLocation.displayName}
                </p>
              )}
            </div>

            {/* 3. Claimed Intervention & Buffer Settings */}
            <div className="flex flex-col gap-3.5 pt-1 border-t border-slate-100">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">
                  Claimed Intervention Type
                </label>
                <select
                  value={activityType}
                  onChange={(e) => setActivityType(e.target.value as ActivityType)}
                  className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white capitalize transition-all cursor-pointer"
                >
                  <option value="check_dam">Check Dam (Nala Bund)</option>
                  <option value="farm_pond">Farm Pond / Reservoir</option>
                  <option value="plantation">Afforestation / Plantation</option>
                  <option value="contour_trench">Contour Trenching (CCT)</option>
                  <option value="desilting">Waterbody Desilting</option>
                  <option value="percolation_tank">Percolation Tank</option>
                  <option value="water_body">General Water Basin</option>
                </select>
              </div>

              {/* Buffer Radius Slider */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700">Analysis Buffer Radius</span>
                  <span className="font-mono text-teal-700 font-bold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    {bufferRadius} meters
                  </span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="2000"
                  step="50"
                  value={bufferRadius}
                  onChange={(e) => setBufferRadius(parseInt(e.target.value))}
                  className="accent-teal-600 cursor-pointer h-2 bg-slate-200 rounded-lg mt-1"
                />
              </div>

              {/* Before/After Delta Toggle */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-700 flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hasBaseline}
                      onChange={(e) => setHasBaseline(e.target.checked)}
                      className="accent-teal-600 rounded"
                    />
                    <span>Before/After Delta (Full Mode)</span>
                  </label>
                  <span className="text-[10px] font-mono font-semibold text-slate-500">
                    {hasBaseline ? "Δ NDVI & Δ NDWI" : "Snapshot"}
                  </span>
                </div>

                {hasBaseline && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] text-slate-500">Baseline Date:</span>
                    <input
                      type="date"
                      value={baselineDate}
                      onChange={(e) => setBaselineDate(e.target.value)}
                      className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono text-slate-800 focus:outline-none focus:border-teal-600"
                    />
                  </div>
                )}
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 p-3 rounded-xl flex items-center gap-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Execute Telemetry Query Button */}
            <button
              onClick={handleExecuteScan}
              disabled={isScanning}
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-md shadow-teal-700/20 transition-all cursor-pointer disabled:opacity-50 active:scale-[0.99]"
            >
              {isScanning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing Sentinel-2 Spectral Indices...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Scan Coordinates Telemetry</span>
                </>
              )}
            </button>

            {/* ── MANUAL SCAN RESULT ACCORDION ───────────────────────────────── */}
            {analysisResult && (
              <div className="flex flex-col gap-4 pt-2 border-t border-slate-100 animate-in fade-in duration-300">
                {/* Health & Status Card */}
                <div className="bg-slate-50/80 rounded-xl p-3.5 border border-slate-200 flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                      Overall Health Score
                    </span>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-2xl font-black font-mono text-slate-900">
                        {analysisResult.health_score ?? 73}
                      </span>
                      <span className="text-xs font-bold font-mono text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                        Grade {analysisResult.health_grade || "B"}
                      </span>
                    </div>
                  </div>

                  <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-slate-200"
                        strokeWidth="3.5"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                      <path
                        className={
                          (analysisResult.health_score ?? 73) >= 80
                            ? "text-emerald-500"
                            : (analysisResult.health_score ?? 73) >= 65
                            ? "text-teal-500"
                            : (analysisResult.health_score ?? 73) >= 50
                            ? "text-amber-500"
                            : "text-rose-500"
                        }
                        strokeDasharray={`${analysisResult.health_score ?? 73}, 100`}
                        strokeWidth="3.5"
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="none"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                      />
                    </svg>
                    <span className="absolute text-[11px] font-black font-mono text-slate-800">
                      {analysisResult.health_score ?? 73}
                    </span>
                  </div>
                </div>

                {/* Spectral Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200 flex flex-col">
                    <span className="text-[10px] text-slate-500 font-sans font-semibold">
                      {hasBaseline ? "Δ NDVI (Vegetation)" : "Current NDVI"}
                    </span>
                    <span className="text-base font-bold text-emerald-700 mt-0.5">
                      {hasBaseline
                        ? (analysisResult.delta_ndvi ?? 0) >= 0
                          ? `+${(analysisResult.delta_ndvi ?? 0).toFixed(3)}`
                          : (analysisResult.delta_ndvi ?? 0).toFixed(3)
                        : (analysisResult.ndvi_tnow ?? 0.28).toFixed(3)}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200 flex flex-col">
                    <span className="text-[10px] text-slate-500 font-sans font-semibold">
                      {hasBaseline ? "Δ NDWI (Water Index)" : "Current NDWI"}
                    </span>
                    <span className="text-base font-bold text-sky-700 mt-0.5">
                      {hasBaseline
                        ? (analysisResult.delta_ndwi ?? 0) >= 0
                          ? `+${(analysisResult.delta_ndwi ?? 0).toFixed(3)}`
                          : (analysisResult.delta_ndwi ?? 0).toFixed(3)
                        : (analysisResult.ndwi_tnow ?? 0.12).toFixed(3)}
                    </span>
                  </div>
                </div>

                {/* Actions: Save Site & View Report */}
                <div className="flex items-center gap-2">
                  {!savedSite ? (
                    <button
                      onClick={handleSaveSite}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-xs transition-all cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Save as Monitored Site</span>
                    </button>
                  ) : (
                    <div className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold text-xs">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Saved ({savedSite.id.substring(0, 6)})</span>
                    </div>
                  )}

                  {savedSite && (
                    <button
                      onClick={() => setReportModalOpen(true)}
                      className="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs border border-slate-200 transition-all cursor-pointer"
                      title="View PDF Report"
                    >
                      <FileDown className="w-3.5 h-3.5" />
                      <span>Report</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* PDF Report Modal */}
      {(savedSite || autoAuditResult?.site) && (
        <ReportModal
          site={(savedSite || autoAuditResult?.site)!}
          photos={autoAuditResult ? [autoAuditResult.photo] : []}
          isOpen={reportModalOpen}
          onClose={() => setReportModalOpen(false)}
        />
      )}
    </>
  );
};
