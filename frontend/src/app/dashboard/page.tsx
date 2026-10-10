"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Navbar } from "../../components/Navbar";
import { StatsBar } from "../../components/StatsBar";
import { AdHocScannerModal } from "../../components/AdHocScannerModal";
import { PhotoUploadModal } from "../../components/PhotoUploadModal";
import { SiteDirectory } from "../../components/SiteDirectory";
import { LocationScannerPanel } from "../../components/LocationScannerPanel";
import { FieldUploadView } from "../../components/FieldUploadView";
import { GeocodedLocation } from "../../components/LocationSearchInput";
import { fetchSites } from "../../lib/api";
import { Site, Photo } from "../../lib/types";
import { Compass, Loader2, Camera, ListFilter, X } from "lucide-react";

// Dynamically import WatershedMap with SSR disabled (Leaflet requires window)
const WatershedMap = dynamic(
  () => import("../../components/WatershedMap").then((mod) => mod.WatershedMap),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[520px] rounded-lg border border-strata-mid bg-surface flex flex-col items-center justify-center text-basalt-light/50 text-sm gap-3">
        <Loader2 className="w-5 h-5 text-reservoir animate-spin" />
        <span className="font-body">Loading map…</span>
      </div>
    ),
  }
);

export default function DashboardPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [activeSearchedPlace, setActiveSearchedPlace] = useState<GeocodedLocation | null>(null);
  const [lowerSectionTab, setLowerSectionTab] = useState<"sites" | "upload">("sites");

  // Ad-hoc scanner modal state
  const [scannerOpen, setScannerOpen] = useState(false);
  const [targetCoords, setTargetCoords] = useState<{ lat: number; lon: number } | null>(null);

  // Photo upload modal state
  const [photoUploadOpen, setPhotoUploadOpen] = useState(false);

  // Load sites on initial mount
  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchSites();
        setSites(data);
      } catch (err) {
        console.error("Failed to load sites", err);
      }
    }
    loadData();
  }, []);

  const handleSelectCoords = async (lat: number, lon: number) => {
    setTargetCoords({ lat, lon });
    setSelectedSite(null);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
      );
      const data = await res.json();
      const placeName = data.display_name?.split(",")[0] || `Point (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
      setActiveSearchedPlace({
        name: placeName,
        displayName: data.display_name || `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
        lat,
        lon,
      });
    } catch {
      setActiveSearchedPlace({
        name: `Coordinates (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`,
        displayName: `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
        lat,
        lon,
      });
    }
  };

  const handleSelectAnomaly = () => {
    const anomalySite = sites.find(
      (s) => s.latest_analysis?.overall_status === "anomaly"
    );
    if (anomalySite) {
      setSelectedSite(anomalySite);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleSiteSaved = (newSite: Site) => {
    setSites((prev) => [newSite, ...prev]);
    setSelectedSite(newSite);
  };

  const handlePhotoUploaded = (photo: Photo) => {
    if (!selectedSite) return;
    setSites((prev) =>
      prev.map((s) => {
        if (s.id === selectedSite.id) {
          return {
            ...s,
            photo_count: (s.photo_count || 0) + 1,
            latest_analysis: s.latest_analysis
              ? {
                  ...s.latest_analysis,
                  photo_agreement: photo.predicted_class === s.activity_type,
                  classified_activity: photo.predicted_class,
                  classification_confidence: photo.classification_confidence,
                }
              : null,
          };
        }
        return s;
      })
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f5f0e6] text-basalt selection:bg-reservoir/20 selection:text-reservoir">
      {/* Top Navbar */}
      <Navbar onScanClick={() => setScannerOpen(true)} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col gap-5">

        {/* ── Context Bar: single compact strip ──────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h1 className="text-lg font-heading font-semibold text-basalt">Dashboard</h1>

          <div className="flex items-center gap-2 flex-wrap">
            {selectedSite ? (
              <div className="flex items-center gap-2 bg-reservoir-faint border border-reservoir/20 text-basalt px-3 py-1.5 rounded-lg text-[12px]">
                <span className="w-1.5 h-1.5 rounded-full bg-reservoir" />
                <span className="font-semibold">
                  {selectedSite.site_code || `SITE-${selectedSite.id.substring(0, 6).toUpperCase()}`}
                </span>
                <span className="text-basalt-light/50 tabular-nums hidden sm:inline">
                  {selectedSite.lat.toFixed(3)}°N, {selectedSite.lon.toFixed(3)}°E
                </span>
                <button
                  onClick={() => setSelectedSite(null)}
                  className="ml-1 text-basalt-light/40 hover:text-basalt p-0.5 rounded transition-colors cursor-pointer"
                  title="Clear selection"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : activeSearchedPlace ? (
              <div className="flex items-center gap-2 bg-sentinel-faint border border-sentinel/20 text-basalt px-3 py-1.5 rounded-lg text-[12px]">
                <span className="w-1.5 h-1.5 rounded-full bg-sentinel" />
                <span className="font-semibold">{activeSearchedPlace.name}</span>
                <span className="text-basalt-light/50 tabular-nums hidden sm:inline">
                  {activeSearchedPlace.lat.toFixed(3)}°, {activeSearchedPlace.lon.toFixed(3)}°
                </span>
                <button
                  onClick={() => {
                    setActiveSearchedPlace(null);
                    setTargetCoords(null);
                  }}
                  className="ml-1 text-basalt-light/40 hover:text-basalt p-0.5 rounded transition-colors cursor-pointer"
                  title="Clear search"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setScannerOpen(true)}
                className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-lg bg-reservoir text-white hover:bg-reservoir-light transition-colors cursor-pointer"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Explore a Site</span>
              </button>
            )}
          </div>
        </div>

        {/* ── MAP + SCANNER PANEL ────────────────────────────────── */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Map Column */}
          <div className="lg:col-span-8">
            <div className="h-[520px] lg:h-[600px] rounded-lg overflow-hidden border border-strata-mid">
              <WatershedMap
                sites={sites}
                selectedSite={selectedSite}
                onSelectSite={(s) => {
                  setSelectedSite(s);
                  setActiveSearchedPlace(null);
                }}
                onSelectCoords={handleSelectCoords}
                targetCoords={targetCoords}
                targetLocationName={activeSearchedPlace?.name}
              />
            </div>
          </div>

          {/* Scanner Panel */}
          <div className="lg:col-span-4">
            <LocationScannerPanel
              selectedSite={selectedSite}
              activeLocation={activeSearchedPlace}
              onLocationSelect={(loc) => {
                setActiveSearchedPlace(loc);
                setSelectedSite(null);
                setTargetCoords({ lat: loc.lat, lon: loc.lon });
              }}
              onClearLocation={() => {
                setActiveSearchedPlace(null);
                setTargetCoords(null);
              }}
              onSiteSaved={handleSiteSaved}
              onUploadPhotoClick={() => setPhotoUploadOpen(true)}
              onClearSelectedSite={() => setSelectedSite(null)}
            />
          </div>
        </section>

        {/* ── STATS STRIP ────────────────────────────────────────── */}
        <StatsBar sites={sites} onSelectAnomaly={handleSelectAnomaly} />

        {/* ── SITES DIRECTORY & FIELD UPLOAD ──────────────────────── */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-strata-mid pb-3">
            <button
              onClick={() => setLowerSectionTab("sites")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors cursor-pointer ${
                lowerSectionTab === "sites"
                  ? "bg-reservoir-faint text-reservoir font-semibold"
                  : "text-basalt-light hover:text-basalt hover:bg-strata/50"
              }`}
            >
              <ListFilter className="w-3.5 h-3.5" />
              <span>Monitored Sites ({sites.length})</span>
            </button>

            <button
              onClick={() => setLowerSectionTab("upload")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors cursor-pointer ${
                lowerSectionTab === "upload"
                  ? "bg-reservoir-faint text-reservoir font-semibold"
                  : "text-basalt-light hover:text-basalt hover:bg-strata/50"
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Field Photos</span>
            </button>
          </div>

          {lowerSectionTab === "sites" ? (
            <SiteDirectory
              sites={sites}
              onSelectSite={(site) => {
                setSelectedSite(site);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            />
          ) : (
            <FieldUploadView sites={sites} onPhotoUploaded={handlePhotoUploaded} />
          )}
        </section>
      </main>

      {/* Ad-Hoc Scanner Modal */}
      <AdHocScannerModal
        initialLat={targetCoords?.lat ?? 19.085}
        initialLon={targetCoords?.lon ?? 74.75}
        isOpen={scannerOpen}
        onClose={() => setScannerOpen(false)}
        onSiteSaved={handleSiteSaved}
      />

      {/* Photo Upload Modal */}
      {selectedSite && (
        <PhotoUploadModal
          site={selectedSite}
          isOpen={photoUploadOpen}
          onClose={() => setPhotoUploadOpen(false)}
          onPhotoUploaded={handlePhotoUploaded}
        />
      )}
    </div>
  );
}
