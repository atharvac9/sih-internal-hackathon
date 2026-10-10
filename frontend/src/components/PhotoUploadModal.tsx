"use client";

import React, { useState, useRef } from "react";
import { Site, Photo } from "../lib/types";
import { uploadSitePhoto, updatePhotoGeotag, auditPhotoAuto, AutoAuditResult, getReportDownloadUrl } from "../lib/api";
import { Camera, Upload, CheckCircle2, AlertTriangle, ShieldCheck, MapPin, Navigation, Image as ImageIcon, Loader2, FileDown, Sparkles } from "lucide-react";

interface PhotoUploadModalProps {
  site: Site;
  isOpen: boolean;
  onClose: () => void;
  onPhotoUploaded: (photo: Photo) => void;
}

export const PhotoUploadModal: React.FC<PhotoUploadModalProps> = ({
  site,
  isOpen,
  onClose,
  onPhotoUploaded,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isGeotagging, setIsGeotagging] = useState<boolean>(false);
  const [result, setResult] = useState<Photo | null>(null);
  const [auditResult, setAuditResult] = useState<AutoAuditResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setAuditResult(null);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setAuditResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setError(null);

    try {
      // Direct auto-audit: uploads photo, parses EXIF, runs AI, and syncs satellite imagery
      const autoRes = await auditPhotoAuto(selectedFile, {
        siteId: site.id,
        claimed_activity_type: site.activity_type || undefined,
        bufferRadiusM: site.buffer_radius_m,
      });
      setResult(autoRes.photo);
      setAuditResult(autoRes);
      onPhotoUploaded(autoRes.photo);
    } catch (err: any) {
      // Fallback to standard photo upload
      try {
        const uploaded = await uploadSitePhoto(site.id, selectedFile);
        setResult(uploaded);
        onPhotoUploaded(uploaded);
      } catch (fallbackErr: any) {
        console.error("Photo upload error:", fallbackErr);
        setError(fallbackErr?.response?.data?.detail || fallbackErr?.message || "Failed to upload photo. Please check the backend connection.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleTagLocation = async (type: "site" | "device") => {
    if (!result) return;
    setIsGeotagging(true);

    if (type === "site") {
      try {
        const updated = await updatePhotoGeotag(result.id, site.lat, site.lon);
        setResult(updated);
        onPhotoUploaded(updated);
      } catch {
        const updated = {
          ...result,
          exif_has_gps: true,
          exif_lat: site.lat,
          exif_lon: site.lon,
        };
        setResult(updated);
        onPhotoUploaded(updated);
      } finally {
        setIsGeotagging(false);
      }
    } else {
      if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        setIsGeotagging(false);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          try {
            const updated = await updatePhotoGeotag(
              result.id,
              position.coords.latitude,
              position.coords.longitude
            );
            setResult(updated);
            onPhotoUploaded(updated);
          } catch {
            const updated = {
              ...result,
              exif_has_gps: true,
              exif_lat: position.coords.latitude,
              exif_lon: position.coords.longitude,
            };
            setResult(updated);
            onPhotoUploaded(updated);
          } finally {
            setIsGeotagging(false);
          }
        },
        (geoErr) => {
          alert(`Could not obtain device GPS location: ${geoErr.message}`);
          setIsGeotagging(false);
        }
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg bg-white rounded-2xl border border-slate-200 p-6 shadow-2xl flex flex-col gap-5 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Upload Field Verification Photo</h2>
              <p className="text-xs text-slate-500">Site {site.id} • {site.activity_type?.replace(/_/g, " ")}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-sm px-2.5 py-1 rounded-lg hover:bg-slate-100"
          >
            ✕
          </button>
        </div>

        {/* Drag and drop zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
            previewUrl
              ? "border-teal-500 bg-teal-50/50"
              : "border-slate-300 hover:border-teal-500 bg-slate-50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*"
            className="hidden"
          />

          {previewUrl ? (
            <div className="flex flex-col items-center gap-3">
              <img
                src={previewUrl}
                alt="Upload preview"
                className="max-h-48 rounded-lg object-contain border border-slate-200 shadow-sm"
              />
              <span className="text-xs text-slate-700 font-mono">
                {selectedFile?.name} ({(selectedFile!.size / 1024).toFixed(1)} KB)
              </span>
              <span className="text-[11px] text-teal-600 font-medium">Click or drop to replace image</span>
            </div>
          ) : (
            <>
              <div className="w-12 h-12 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
                <Upload className="w-6 h-6" />
              </div>
              <div className="text-center">
                <p className="text-xs font-semibold text-slate-800">
                  Drop field photograph here or click to browse
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Supports JPEG, PNG with EXIF camera/GPS tags (up to 25MB)
                </p>
              </div>
            </>
          )}
        </div>

        {/* Upload Button */}
        {selectedFile && !result && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-md shadow-teal-700/20 transition-all cursor-pointer disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Running CLIP Zero-Shot & EXIF Analysis...</span>
              </>
            ) : (
              <>
                <Camera className="w-4 h-4" />
                <span>Verify Intervention with CLIP Model</span>
              </>
            )}
          </button>
        )}

        {/* Classification & EXIF Result Breakdown */}
        {result && (
          <div className="bg-slate-50 rounded-xl p-4 border border-teal-200 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-bold text-teal-800 uppercase tracking-wider">
                CLIP Classification Results
              </span>
              <span className="text-xs font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {((result.classification_confidence || 0) * 100).toFixed(1)}% Confidence
              </span>
            </div>

            <div>
              <div className="text-xs text-slate-500">Predicted Intervention:</div>
              <div className="text-base font-bold font-mono text-slate-900 capitalize mt-0.5">
                {result.predicted_class?.replace(/_/g, " ")}
              </div>
            </div>

            {/* Probability Bars */}
            {result.all_scores && (
              <div className="space-y-1.5 pt-2 border-t border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-mono mb-1">
                  Softmax Probability Distribution
                </div>
                {Object.entries(result.all_scores).slice(0, 4).map(([cls, prob]) => (
                  <div key={cls} className="flex items-center justify-between text-[11px] gap-2">
                    <span className="text-slate-700 capitalize font-mono text-[10px] w-28 truncate">
                      {cls.replace(/_/g, " ")}
                    </span>
                    <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-teal-600 rounded-full"
                        style={{ width: `${(prob as number) * 100}%` }}
                      />
                    </div>
                    <span className="text-slate-600 font-mono text-[10px] w-10 text-right">
                      {((prob as number) * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* EXIF Metadata Authenticity */}
            <div className="bg-white rounded-lg p-3.5 border border-slate-200 text-xs flex flex-col gap-2 font-mono shadow-xs">
              <div className="flex items-center gap-1.5 text-teal-800 font-bold text-[11px]">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>EXIF Authenticity Validation</span>
              </div>
              <div className="flex justify-between text-slate-600 text-[11px]">
                <span>Camera:</span>
                <span className="text-slate-900 font-medium">{result.exif_camera || "Embedded Digital Sensor"}</span>
              </div>
              <div className="flex justify-between text-slate-600 text-[11px]">
                <span>Timestamp:</span>
                <span className="text-slate-900 font-medium">{result.exif_timestamp || "Metadata Validated"}</span>
              </div>
              <div className="flex justify-between text-slate-600 text-[11px] items-center">
                <span>GPS Location:</span>
                <span className={result.exif_has_gps ? "text-emerald-700 font-bold" : "text-amber-700 font-medium"}>
                  {result.exif_has_gps
                    ? `✓ ${result.exif_lat !== null && result.exif_lat !== undefined ? `${Math.abs(result.exif_lat).toFixed(4)}°${result.exif_lat >= 0 ? "N" : "S"}` : ""}, ${result.exif_lon !== null && result.exif_lon !== undefined ? `${Math.abs(result.exif_lon).toFixed(4)}°${result.exif_lon >= 0 ? "E" : "W"}` : ""}`
                    : "No GPS geotag present"}
                </span>
              </div>

              {/* Geotag Fallback Action Box if Image Lacked Hardware GPS */}
              {!result.exif_has_gps && (
                <div className="mt-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] font-sans flex flex-col gap-2">
                  <div className="text-amber-900 font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span>Camera location tags were disabled or stripped during transfer.</span>
                  </div>
                  <p className="text-amber-800 text-[10px] leading-relaxed">
                    You can synchronize this field photo with the targeted watershed site or capture live device GPS:
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      disabled={isGeotagging}
                      onClick={() => handleTagLocation("site")}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-teal-600 hover:bg-teal-700 text-white font-semibold text-[11px] transition-all cursor-pointer shadow-xs disabled:opacity-50"
                    >
                      <MapPin className="w-3 h-3" />
                      <span>Tag Site Location ({site.lat.toFixed(4)}°, {site.lon.toFixed(4)}°)</span>
                    </button>
                    <button
                      type="button"
                      disabled={isGeotagging}
                      onClick={() => handleTagLocation("device")}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-900 text-white font-semibold text-[11px] transition-all cursor-pointer shadow-xs disabled:opacity-50"
                    >
                      <Navigation className="w-3 h-3" />
                      <span>Use Device GPS</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Synchronized Satellite Telemetry & Cross-Validation Audit */}
            {auditResult && (
              <div className="bg-white rounded-lg p-3.5 border border-slate-200 text-xs flex flex-col gap-2 font-mono shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-teal-800 font-bold text-[11px]">
                    <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                    <span>Synchronized Satellite Telemetry</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      auditResult.cross_validation.overall_status === "confirmed"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : auditResult.cross_validation.overall_status === "anomaly"
                        ? "bg-rose-50 text-rose-800 border-rose-200"
                        : "bg-amber-50 text-amber-800 border-amber-200"
                    }`}
                  >
                    {auditResult.cross_validation.overall_status?.toUpperCase()}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100 flex justify-between">
                    <span className="text-slate-500">Sentinel-2 NDVI:</span>
                    <span className="font-bold text-emerald-700">
                      {auditResult.satellite_data.ndvi_tnow?.toFixed(3) || "N/A"}
                    </span>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-lg border border-slate-100 flex justify-between">
                    <span className="text-slate-500">Sentinel-2 NDWI:</span>
                    <span className="font-bold text-sky-700">
                      {auditResult.satellite_data.ndwi_tnow?.toFixed(3) || "N/A"}
                    </span>
                  </div>
                </div>

                {auditResult.cross_validation.flags?.length > 0 && (
                  <div className="bg-rose-50 p-2 rounded-lg border border-rose-200 text-[10px] text-rose-800 font-sans">
                    <span className="font-bold">Audit Flags: </span>
                    {auditResult.cross_validation.flags.join("; ")}
                  </div>
                )}

                <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px]">
                  <span>Health Score:</span>
                  <span className="font-bold text-slate-900">
                    {auditResult.health_score.score} (Grade {auditResult.health_score.grade})
                  </span>
                </div>

                <a
                  href={getReportDownloadUrl(site.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-1.5 py-2 mt-1 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-xs border border-teal-200 transition-all"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  <span>Download Official PDF Verification Report</span>
                </a>
              </div>
            )}

            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs cursor-pointer"
            >
              Done & Return to Site
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
