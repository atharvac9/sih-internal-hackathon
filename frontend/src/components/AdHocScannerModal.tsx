"use client";

import React, { useState, useEffect } from "react";
import { Crosshair, Check, Sparkles, AlertCircle, ArrowRight, Loader2, MapPin } from "lucide-react";
import { runAdHocAnalysis, createSite } from "../lib/api";
import { ActivityType, AnalysisResult, Site } from "../lib/types";
import { HealthGauge } from "./HealthGauge";
import { LocationSearchInput } from "./LocationSearchInput";

interface AdHocScannerModalProps {
  initialLat: number;
  initialLon: number;
  isOpen: boolean;
  onClose: () => void;
  onSiteSaved: (site: Site) => void;
}

export const AdHocScannerModal: React.FC<AdHocScannerModalProps> = ({
  initialLat,
  initialLon,
  isOpen,
  onClose,
  onSiteSaved,
}) => {
  const [lat, setLat] = useState<number>(initialLat);
  const [lon, setLon] = useState<number>(initialLon);

  useEffect(() => {
    setLat(initialLat);
    setLon(initialLon);
  }, [initialLat, initialLon]);
  const [activityType, setActivityType] = useState<ActivityType>("check_dam");
  const [baselineDate, setBaselineDate] = useState<string>("2023-01-15");
  const [hasBaseline, setHasBaseline] = useState<boolean>(true);
  const [bufferRadius, setBufferRadius] = useState<number>(500);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [savedSite, setSavedSite] = useState<Site | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleScan = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await runAdHocAnalysis({
        lat,
        lon,
        claimed_activity_type: activityType,
        baseline_date: hasBaseline ? baselineDate : undefined,
        buffer_radius_m: bufferRadius,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to execute telemetry analysis");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSite = async () => {
    try {
      const newSite = await createSite({
        lat,
        lon,
        activity_type: activityType,
        buffer_radius_m: bufferRadius,
        baseline_date: hasBaseline ? baselineDate : undefined,
        description: `Ad-hoc scanned site at ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
      });
      // Attach latest analysis result
      newSite.latest_analysis = result;
      setSavedSite(newSite);
      onSiteSaved(newSite);
    } catch (err: any) {
      setError(err.message || "Failed to save site");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-xl bg-white rounded-2xl border border-slate-200 p-6 shadow-2xl flex flex-col gap-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
              <Crosshair className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Watershed Telemetry Scanner</h2>
              <p className="text-xs text-slate-500">Compute vegetation and moisture indices for target coordinates</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-sm px-2.5 py-1 rounded-lg hover:bg-slate-100"
          >
            ✕
          </button>
        </div>

        {/* 1. Location Search Input */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-700 flex items-center justify-between">
            <span>Search Preferred Location</span>
            <span className="text-[10px] font-normal text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
              Auto-fetches coordinates
            </span>
          </label>
          <LocationSearchInput
            onLocationSelect={(loc) => {
              setLat(loc.lat);
              setLon(loc.lon);
            }}
            placeholder="Type city, village, river (e.g. Pune, Godavari)..."
          />
        </div>

        {/* Input Parameters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Coordinates */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-700">Latitude (°N)</label>
            <input
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => setLat(parseFloat(e.target.value))}
              className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-700">Longitude (°E)</label>
            <input
              type="number"
              step="0.0001"
              value={lon}
              onChange={(e) => setLon(parseFloat(e.target.value))}
              className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white"
            />
          </div>

          {/* Activity Type */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-slate-700">Claimed Intervention Type</label>
            <select
              value={activityType}
              onChange={(e) => setActivityType(e.target.value as ActivityType)}
              className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white capitalize"
            >
              <option value="check_dam">Check Dam (Nala Bund)</option>
              <option value="farm_pond">Farm Pond / Reservoir</option>
              <option value="plantation">Afforestation / Plantation</option>
              <option value="contour_trench">Contour Trenching (CCT)</option>
              <option value="desilting">Waterbody Desilting</option>
              <option value="gabion">Gabion Structure</option>
              <option value="percolation_tank">Percolation Tank</option>
            </select>
          </div>

          {/* Buffer Radius */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700">Buffer Radius</label>
              <span className="text-xs font-mono text-teal-600 font-bold">{bufferRadius}m</span>
            </div>
            <input
              type="range"
              min="100"
              max="2000"
              step="50"
              value={bufferRadius}
              onChange={(e) => setBufferRadius(parseInt(e.target.value))}
              className="accent-teal-600 cursor-pointer h-2 bg-slate-200 rounded-lg mt-2"
            />
          </div>
        </div>

        {/* Baseline Date Toggle */}
        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-slate-700 flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={hasBaseline}
                onChange={(e) => setHasBaseline(e.target.checked)}
                className="accent-teal-600 rounded"
              />
              <span>Compute Before/After Delta (Full Mode)</span>
            </label>
            <span className="text-[11px] text-slate-500 font-medium">
              {hasBaseline ? "Δ NDVI & Δ NDWI" : "Snapshot Only"}
            </span>
          </div>

          {hasBaseline && (
            <div className="mt-1 flex items-center gap-2">
              <span className="text-xs text-slate-500">Baseline Date:</span>
              <input
                type="date"
                value={baselineDate}
                onChange={(e) => setBaselineDate(e.target.value)}
                className="bg-white border border-slate-200 rounded-md px-2.5 py-1 text-xs font-mono text-slate-900 focus:outline-none focus:border-teal-600"
              />
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-3 rounded-lg flex items-center gap-2 text-xs text-red-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Trigger Button */}
        <button
          onClick={handleScan}
          disabled={isLoading}
          className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-md shadow-teal-700/20 transition-all cursor-pointer disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Computing Watershed Telemetry Indices...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Execute Telemetry Query</span>
            </>
          )}
        </button>

        {/* Results Area */}
        {result && (
          <div className="bg-slate-50 rounded-xl p-4 border border-teal-200 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-bold text-teal-800 uppercase tracking-wider">Analysis Result</span>
              <span className="text-xs font-mono text-slate-500">Spectral Telemetry Engine</span>
            </div>

            <HealthGauge
              score={result.health_score}
              grade={result.health_grade}
              ndviDelta={result.delta_ndvi}
              ndwiDelta={result.delta_ndwi}
              status={result.overall_status}
            />

            {savedSite ? (
              <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-lg flex items-center justify-between text-xs text-emerald-800">
                <span className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600" />
                  Site saved as monitored site #{savedSite.id}
                </span>
                <button
                  onClick={onClose}
                  className="px-3 py-1 rounded bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500"
                >
                  View in Map
                </button>
              </div>
            ) : (
              <button
                onClick={handleSaveSite}
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium transition-all cursor-pointer shadow-xs"
              >
                <span>Save this location as a permanent Monitored Site</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
