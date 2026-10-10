"use client";

import React, { useState } from "react";
import { Site, AnalysisResult } from "../lib/types";
import { HealthGauge } from "./HealthGauge";
import { ReportModal } from "./ReportModal";
import {
  FileDown,
  Camera,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  Printer,
} from "lucide-react";

interface SiteInspectorProps {
  site: Site;
  onUploadPhotoClick: (site: Site) => void;
  onClose?: () => void;
}

export const SiteInspector: React.FC<SiteInspectorProps> = ({
  site,
  onUploadPhotoClick,
  onClose,
}) => {
  const [reportModalOpen, setReportModalOpen] = useState(false);

  const analysis = site.latest_analysis;
  const isAnomaly = analysis?.overall_status === "anomaly";
  const isConfirmed = analysis?.overall_status === "confirmed";

  const displayName =
    site.site_code ||
    (site.description && !site.description.startsWith("Ad-hoc")
      ? site.description
      : `Site at ${site.lat.toFixed(3)}°N, ${site.lon.toFixed(3)}°E`);

  return (
    <>
      <div className="glass-panel rounded-2xl p-5 border border-slate-200 bg-white shadow-sm flex flex-col gap-5 text-slate-800">
        {/* Header Bar */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xl font-bold text-slate-900">{displayName}</span>
              <span
                className={`text-xs font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                  isAnomaly
                    ? "bg-red-50 border-red-200 text-red-700"
                    : isConfirmed
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                    : "bg-amber-50 border-amber-200 text-amber-700"
                }`}
              >
                {analysis?.overall_status || "Pending Analysis"}
              </span>
            </div>
            <div className="text-sm font-semibold text-teal-700 mt-1 capitalize">
              {site.activity_type ? site.activity_type.replace(/_/g, " ") : "Unspecified Activity"}
            </div>
            <div className="text-xs font-mono text-slate-500 mt-0.5">
              {site.lat.toFixed(4)}°N, {site.lon.toFixed(4)}°E • Radius: {site.buffer_radius_m}m
            </div>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 text-sm p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              ✕
            </button>
          )}
        </div>

        {/* Description */}
        {site.description && (
          <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
            {site.description}
          </div>
        )}

        {/* Health Score Gauge */}
        {analysis && (
          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/80">
            <HealthGauge
              score={analysis.health_score}
              grade={analysis.health_grade}
              ndviDelta={analysis.delta_ndvi}
              ndwiDelta={analysis.delta_ndwi}
              status={analysis.overall_status}
            />
          </div>
        )}

        {/* Anomaly & Flags Alert Banner */}
        {isAnomaly && analysis?.flags && analysis.flags.length > 0 && (
          <div className="bg-red-50/80 border border-red-200 p-3.5 rounded-xl flex flex-col gap-2">
            <div className="flex items-center gap-2 text-red-700 font-semibold text-xs">
              <ShieldAlert className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>Cross-Validation Discrepancies Detected</span>
            </div>
            <ul className="text-xs text-red-700 list-disc list-inside space-y-1 pl-1">
              {analysis.flags.map((flag, idx) => (
                <li key={idx}>{flag}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Telemetry Details */}
        {analysis && (
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-[11px] text-slate-500 uppercase font-mono">NDVI (Vegetation)</div>
              <div className="text-base font-bold font-mono text-slate-900 mt-1">
                {analysis.ndvi_tnow?.toFixed(3) ?? "N/A"}
              </div>
              {analysis.ndvi_t0 !== null && (
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  Baseline: {analysis.ndvi_t0.toFixed(3)}
                </div>
              )}
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div className="text-[11px] text-slate-500 uppercase font-mono">NDWI (Water Index)</div>
              <div className="text-base font-bold font-mono text-slate-900 mt-1">
                {analysis.ndwi_tnow?.toFixed(3) ?? "N/A"}
              </div>
              {analysis.ndwi_t0 !== null && (
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                  Baseline: {analysis.ndwi_t0.toFixed(3)}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Cross-Validation Agreement Breakdown */}
        {analysis && (
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs flex flex-col gap-2">
            <div className="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>Cross-Validation Matrix</span>
              <span className="text-[10px] font-mono text-slate-500">
                Source: Multispectral Sensors
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-t border-slate-200">
              <span className="text-slate-600">Spectral Telemetry Agreement</span>
              <span
                className={`font-mono font-semibold ${
                  analysis.satellite_agreement ? "text-emerald-700" : "text-red-600"
                }`}
              >
                {analysis.satellite_agreement ? "CONFIRMED ✓" : "DISCORDANT ⚠"}
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-t border-slate-200">
              <span className="text-slate-600">CLIP Photo Match</span>
              <span
                className={`font-mono font-semibold ${
                  analysis.photo_agreement === true
                    ? "text-emerald-700"
                    : analysis.photo_agreement === false
                    ? "text-red-600"
                    : "text-slate-500"
                }`}
              >
                {analysis.photo_agreement === true
                  ? "MATCHED ✓"
                  : analysis.photo_agreement === false
                  ? "MISMATCH ⚠"
                  : "PENDING PHOTO"}
              </span>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 mt-1 pt-3 border-t border-slate-100">
          <button
            onClick={() => onUploadPhotoClick(site)}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-xs shadow-sm transition-all cursor-pointer"
          >
            <Camera className="w-4 h-4" />
            <span>Upload Field Verification Photo</span>
          </button>

          <button
            onClick={() => setReportModalOpen(true)}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 font-medium text-xs transition-all text-center cursor-pointer shadow-sm"
          >
            <Printer className="w-4 h-4 text-teal-700" />
            <span>Export Official PDF Report</span>
            <Sparkles className="w-3 h-3 text-teal-600 ml-1" />
          </button>
        </div>
      </div>

      {/* Official Report & Print Modal */}
      <ReportModal
        site={site}
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
      />
    </>
  );
};
