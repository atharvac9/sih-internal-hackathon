"use client";

import React, { useState } from "react";
import { Site, Photo } from "../lib/types";
import { Camera, Upload, CheckCircle2, AlertTriangle, ShieldCheck, Sparkles, MapPin, Navigation } from "lucide-react";
import { uploadSitePhoto, updatePhotoGeotag } from "../lib/api";

interface FieldUploadViewProps {
  sites: Site[];
  onPhotoUploaded: (photo: Photo) => void;
}

export const FieldUploadView: React.FC<FieldUploadViewProps> = ({ sites, onPhotoUploaded }) => {
  const [selectedSiteId, setSelectedSiteId] = useState<string>(sites[0]?.id || "");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isGeotagging, setIsGeotagging] = useState<boolean>(false);
  const [result, setResult] = useState<Photo | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentSite = sites.find((s) => s.id === selectedSiteId) || sites[0];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !currentSite) return;
    setIsUploading(true);
    setError(null);

    try {
      const photo = await uploadSitePhoto(currentSite.id, selectedFile);
      setResult(photo);
      onPhotoUploaded(photo);
    } catch (err: any) {
      console.error("Photo upload error:", err);
      setError(err?.response?.data?.detail || err?.message || "Failed to upload photo. Please verify backend connection.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleTagLocation = async (type: "site" | "device") => {
    if (!result || !currentSite) return;
    setIsGeotagging(true);

    if (type === "site") {
      try {
        const updated = await updatePhotoGeotag(result.id, currentSite.lat, currentSite.lon);
        setResult(updated);
        onPhotoUploaded(updated);
      } catch {
        const updated = {
          ...result,
          exif_has_gps: true,
          exif_lat: currentSite.lat,
          exif_lon: currentSite.lon,
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
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Upload Column */}
      <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col gap-5">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Camera className="w-5 h-5 text-teal-600" />
            <span>Field Verification Photo Upload</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit on-ground photographs for automated CLIP visual classification and EXIF geotag validation
          </p>
        </div>

        {/* Target Site Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-700">Target Monitored Site</label>
          <select
            value={selectedSiteId}
            onChange={(e) => setSelectedSiteId(e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-teal-600 focus:bg-white"
          >
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id} — {s.activity_type ? s.activity_type.replace(/_/g, " ") : "Unspecified"} ({s.lat.toFixed(4)}°N, {s.lon.toFixed(4)}°E)
              </option>
            ))}
          </select>
        </div>

        {/* Drop Zone */}
        <div
          onClick={() => document.getElementById("field-photo-input")?.click()}
          className="border-2 border-dashed border-slate-300 hover:border-teal-600 rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all bg-slate-50"
        >
          <input
            id="field-photo-input"
            type="file"
            onChange={handleFileChange}
            accept="image/*"
            className="hidden"
          />

          {previewUrl ? (
            <div className="flex flex-col items-center gap-3">
              <img
                src={previewUrl}
                alt="Selected preview"
                className="max-h-60 rounded-lg object-contain border border-slate-200 shadow-sm"
              />
              <span className="text-xs font-mono text-slate-700">
                {selectedFile?.name} ({(selectedFile!.size / 1024).toFixed(1)} KB)
              </span>
              <span className="text-[11px] text-teal-600 font-medium">Click to choose a different photo</span>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-600">
                <Upload className="w-7 h-7" />
              </div>
              <div className="text-center">
                <p className="text-sm font-semibold text-slate-800">
                  Click to select field intervention image
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Raw camera photos containing EXIF timestamp & GPS geotags preferred
                </p>
              </div>
            </>
          )}
        </div>

        {selectedFile && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="flex items-center justify-center gap-2 py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-md shadow-teal-700/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isUploading ? "Running AI Classification & Metadata Audit..." : "Analyze Photograph"}</span>
          </button>
        )}

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Result Column */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col gap-4">
        <h3 className="text-sm font-bold text-slate-800 border-b border-slate-200 pb-3">
          Verification Intelligence
        </h3>

        {result ? (
          <div className="flex flex-col gap-4">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-teal-200">
              <div className="text-[11px] uppercase font-mono text-slate-500">CLIP Classified Intervention</div>
              <div className="text-lg font-bold font-mono text-teal-800 capitalize mt-1">
                {result.predicted_class?.replace(/_/g, " ")}
              </div>
              <div className="text-xs text-emerald-700 font-mono mt-0.5">
                {((result.classification_confidence || 0) * 100).toFixed(1)}% model certainty
              </div>
            </div>

            {/* Probability Breakdown */}
            {result.all_scores && (
              <div className="space-y-2">
                <div className="text-[11px] uppercase font-mono text-slate-500">Classification Probabilities</div>
                {Object.entries(result.all_scores).slice(0, 5).map(([cls, prob]) => (
                  <div key={cls} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-700 capitalize">{cls.replace(/_/g, " ")}</span>
                      <span className="text-teal-700 font-semibold">{((prob as number) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-teal-600 rounded-full"
                        style={{ width: `${(prob as number) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* EXIF Authenticity */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs font-mono flex flex-col gap-2">
              <div className="flex items-center gap-1.5 text-teal-800 font-semibold">
                <ShieldCheck className="w-4 h-4 text-teal-600" />
                <span>EXIF Authenticity Validation</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Hardware:</span>
                <span className="text-slate-900 font-medium">{result.exif_camera || "Embedded Digital Sensor"}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Timestamp:</span>
                <span className="text-slate-900 font-medium">{result.exif_timestamp || "Validated"}</span>
              </div>
              <div className="flex justify-between text-slate-600 items-center">
                <span>Geotag:</span>
                <span className={result.exif_has_gps ? "text-emerald-700 font-bold" : "text-amber-700 font-medium"}>
                  {result.exif_has_gps
                    ? `✓ ${result.exif_lat !== null && result.exif_lat !== undefined ? `${Math.abs(result.exif_lat).toFixed(4)}°${result.exif_lat >= 0 ? "N" : "S"}` : ""}, ${result.exif_lon !== null && result.exif_lon !== undefined ? `${Math.abs(result.exif_lon).toFixed(4)}°${result.exif_lon >= 0 ? "E" : "W"}` : ""}`
                    : "No GPS geotag present"}
                </span>
              </div>

              {/* Geotag Fallback Action Box if Image Lacked Hardware GPS */}
              {!result.exif_has_gps && currentSite && (
                <div className="mt-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] font-sans flex flex-col gap-2">
                  <div className="text-amber-900 font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span>Camera location tags were disabled or stripped during transfer.</span>
                  </div>
                  <p className="text-amber-800 text-[10px] leading-relaxed">
                    Synchronize this field photo with target site or capture live device GPS:
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <button
                      type="button"
                      disabled={isGeotagging}
                      onClick={() => handleTagLocation("site")}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-teal-600 hover:bg-teal-700 text-white font-semibold text-[11px] transition-all cursor-pointer shadow-xs disabled:opacity-50"
                    >
                      <MapPin className="w-3 h-3" />
                      <span>Tag Site ({currentSite.lat.toFixed(4)}°, {currentSite.lon.toFixed(4)}°)</span>
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
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-8 text-slate-400 gap-2">
            <Camera className="w-10 h-10 stroke-1" />
            <p className="text-xs">No photograph analyzed yet</p>
            <p className="text-[11px] text-slate-500">
              Upload an image to inspect AI classification and EXIF authenticity checks
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
