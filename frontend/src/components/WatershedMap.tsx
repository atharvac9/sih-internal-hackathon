"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { Site } from "../lib/types";
import {
  Compass,
  MapPin,
  Layers,
  Sparkles,
  Crosshair,
  Globe2,
} from "lucide-react";
import type L from "leaflet";

interface WatershedMapProps {
  sites: Site[];
  selectedSite: Site | null;
  onSelectSite: (site: Site) => void;
  onSelectCoords: (lat: number, lon: number) => void;
  targetCoords?: { lat: number; lon: number } | null;
  targetLocationName?: string | null;
}

type MapLayerType = "osm" | "satellite";

export const WatershedMap: React.FC<WatershedMapProps> = ({
  sites,
  selectedSite,
  onSelectSite,
  onSelectCoords,
  targetCoords,
  targetLocationName,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const siteMarkersRef = useRef<L.LayerGroup | null>(null);
  const targetMarkerRef = useRef<L.Marker | null>(null);
  const leafletLibRef = useRef<typeof L | null>(null);

  const [activeLayer, setActiveLayer] = useState<MapLayerType>("osm");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState<boolean>(false);

  // Keep latest onSelectCoords in ref to avoid map recreation
  const onSelectCoordsRef = useRef(onSelectCoords);
  onSelectCoordsRef.current = onSelectCoords;

  // Show a temporary toast message
  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  }, []);

  // Tile layer URLs - Street Map and Satellite Imagery (Buffered & optimized)
  const getTileLayer = useCallback((layer: MapLayerType, L_lib: typeof L) => {
    if (layer === "satellite") {
      return L_lib.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          attribution: "&copy; Esri, Maxar, Earthstar Geographics",
          keepBuffer: 3,
          updateWhenIdle: true,
          updateWhenZooming: false,
        }
      );
    } else {
      return L_lib.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
          keepBuffer: 3,
          updateWhenIdle: true,
          updateWhenZooming: false,
        }
      );
    }
  }, []);

  // Initialize Leaflet map ONCE on mount
  useEffect(() => {
    let isMounted = true;

    async function initMap() {
      if (!mapContainerRef.current || mapInstanceRef.current) return;

      const leafletModule = await import("leaflet");
      const L = (leafletModule.default || leafletModule) as unknown as typeof import("leaflet");
      if (!isMounted || !mapContainerRef.current) return;

      leafletLibRef.current = L;

      // Center on India or targetCoords
      const initialLat = targetCoords ? targetCoords.lat : 20.5937;
      const initialLon = targetCoords ? targetCoords.lon : 78.9629;
      const initialZoom = targetCoords ? 13 : 6;

      const map = L.map(mapContainerRef.current, {
        center: [initialLat, initialLon],
        zoom: initialZoom,
        zoomControl: false,
        attributionControl: false,
        preferCanvas: true,
      });

      // Add zoom control at bottom-right
      L.control
        .zoom({
          position: "bottomright",
        })
        .addTo(map);

      // Add default tile layer (OpenStreetMap / clean cartography)
      const baseTile = getTileLayer("osm", L);
      baseTile.addTo(map);
      tileLayerRef.current = baseTile;

      // Layer group for sites
      const sitesGroup = L.layerGroup().addTo(map);
      siteMarkersRef.current = sitesGroup;

      // Map click handler to select coordinates
      map.on("click", (e: L.LeafletMouseEvent) => {
        const lat = Number(e.latlng.lat.toFixed(4));
        const lon = Number(e.latlng.lng.toFixed(4));
        onSelectCoordsRef.current(lat, lon);
        showToast(`Selected coordinates: ${lat}°N, ${lon}°E`);
      });

      mapInstanceRef.current = map;
      setMapReady(true);
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        targetMarkerRef.current = null;
        siteMarkersRef.current = null;
        setMapReady(false);
      }
    };
  }, []);

  // Handle Layer Switching
  const handleLayerChange = (newLayer: MapLayerType) => {
    setActiveLayer(newLayer);
    const map = mapInstanceRef.current;
    const L = leafletLibRef.current;
    if (!map || !L) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }
    const newTile = getTileLayer(newLayer, L);
    newTile.addTo(map);
    tileLayerRef.current = newTile;
  };

  // Render Site Markers and Buffers
  useEffect(() => {
    const map = mapInstanceRef.current;
    const sitesGroup = siteMarkersRef.current;
    const L = leafletLibRef.current;
    if (!map || !sitesGroup || !L || !mapReady) return;

    sitesGroup.clearLayers();

    sites.forEach((site) => {
      const isSelected = selectedSite?.id === site.id;
      const isAnomaly = site.latest_analysis?.overall_status === "anomaly";
      const isConfirmed = site.latest_analysis?.overall_status === "confirmed";

      const color = isAnomaly ? "#ef4444" : isConfirmed ? "#10b981" : "#f59e0b";

      // 500m Buffer circle
      const buffer = L.circle([site.lat, site.lon], {
        radius: site.buffer_radius_m || 500,
        color: color,
        weight: isSelected ? 2 : 1,
        dashArray: isSelected ? undefined : "4, 6",
        fillColor: color,
        fillOpacity: isSelected ? 0.2 : 0.08,
      });
      buffer.addTo(sitesGroup);

      // Custom marker icon (optimized - no continuous compositor thrash)
      const iconHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group">
          <div class="absolute w-8 h-8 rounded-full opacity-30" style="border: 2px solid ${color};"></div>
          <div class="relative w-7 h-7 rounded-full flex items-center justify-center shadow-md border-2" 
               style="background-color: #0f172a; border-color: ${color};">
            <span class="text-[10px] font-bold font-mono" style="color: ${color}">
              ${site.site_code || site.id.substring(0, 3)}
            </span>
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: "custom-site-pin",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([site.lat, site.lon], { icon: customIcon });

      marker.bindTooltip(
        `
        <div class="font-sans">
          <div class="font-bold text-white flex items-center gap-1.5">
            <span>${site.site_code || site.id}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded capitalize" style="background: ${color}22; color: ${color};">
              ${(site.activity_type || "watershed").replace(/_/g, " ")}
            </span>
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            ${site.description || `${site.lat.toFixed(4)}°N, ${site.lon.toFixed(4)}°E`}
          </div>
          ${
            site.latest_analysis
              ? `<div class="text-[10px] font-mono text-teal-300 mt-0.5">Health Score: ${site.latest_analysis.health_score} (Grade ${site.latest_analysis.health_grade})</div>`
              : ""
          }
        </div>
        `,
        { direction: "top", offset: [0, -10] }
      );

      marker.on("click", () => {
        onSelectSite(site);
      });

      marker.addTo(sitesGroup);
    });
  }, [sites, selectedSite, onSelectSite, mapReady]);

  // Update Target Pin and smoothly fly map camera when targetCoords or targetLocationName changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    const L = leafletLibRef.current;
    if (!map || !L || !mapReady) return;

    if (targetCoords) {
      const popupHtml = `
        <div class="text-xs font-sans p-1 min-w-[170px]">
          <div class="font-bold text-teal-800 flex items-center gap-1.5 border-b border-slate-200 pb-1">
            <span>🎯 ${targetLocationName || "Target Location"}</span>
          </div>
          <div class="font-mono text-slate-700 mt-1.5 font-semibold text-[11px]">
            ${targetCoords.lat.toFixed(4)}°N, ${targetCoords.lon.toFixed(4)}°E
          </div>
          <div class="text-[10px] text-teal-600 mt-1 font-medium">
            ✓ Ready for watershed telemetry
          </div>
        </div>
      `;

      if (targetMarkerRef.current) {
        targetMarkerRef.current.setLatLng([targetCoords.lat, targetCoords.lon]);
        targetMarkerRef.current.setPopupContent(popupHtml);
        targetMarkerRef.current.openPopup();
      } else {
        const targetHtml = `
          <div class="relative flex items-center justify-center">
            <div class="absolute w-11 h-11 rounded-full border-2 border-teal-500/40"></div>
            <div class="w-8 h-8 rounded-full bg-teal-500/25 border-2 border-teal-600 flex items-center justify-center shadow-lg">
              <div class="w-2.5 h-2.5 rounded-full bg-teal-600"></div>
            </div>
          </div>
        `;

        const targetIcon = L.divIcon({
          html: targetHtml,
          className: "target-crosshair-pin",
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        });

        const newTarget = L.marker([targetCoords.lat, targetCoords.lon], {
          icon: targetIcon,
          zIndexOffset: 1000,
        }).addTo(map);

        newTarget.bindPopup(popupHtml);
        newTarget.openPopup();
        targetMarkerRef.current = newTarget;
      }

      // Fly camera directly to searched location
      map.flyTo([targetCoords.lat, targetCoords.lon], 13, { duration: 1.2 });
    } else if (targetMarkerRef.current) {
      map.removeLayer(targetMarkerRef.current);
      targetMarkerRef.current = null;
    }
  }, [targetCoords, targetLocationName, mapReady]);

  // Fly camera to selected site when selectedSite changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedSite || !mapReady) return;
    map.flyTo([selectedSite.lat, selectedSite.lon], 14, { duration: 1.2 });
  }, [selectedSite, mapReady]);

  // Reset View to sites or overview
  const handleResetView = () => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (sites.length > 0) {
      map.flyTo([sites[0].lat, sites[0].lon], 12, { duration: 1 });
    } else {
      map.flyTo([20.5937, 78.9629], 5, { duration: 1 });
    }
  };

  return (
    <div className="relative w-full h-full min-h-[520px] bg-slate-100 rounded-2xl border border-slate-200 overflow-hidden shadow-xs flex flex-col">
      {/* ── Top-Right Map Controls: Street Map, Satellite & Reset ──────────── */}
      <div className="absolute top-3 right-3 z-[1000] flex items-center gap-1.5 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl p-1 shadow-md pointer-events-auto">
        <button
          onClick={() => handleLayerChange("osm")}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeLayer === "osm"
              ? "bg-teal-600 text-white shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          }`}
          title="OpenStreetMap Street View"
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="inline">Street Map</span>
        </button>

        <button
          onClick={() => handleLayerChange("satellite")}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
            activeLayer === "satellite"
              ? "bg-teal-600 text-white shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
          }`}
          title="Satellite Imagery View"
        >
          <Globe2 className="w-3.5 h-3.5" />
          <span className="inline">Satellite</span>
        </button>

        <div className="w-px h-4 bg-slate-200 mx-1" />

        <button
          onClick={handleResetView}
          className="flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all cursor-pointer"
          title="Reset Map View"
        >
          <Compass className="w-3.5 h-3.5 text-teal-600" />
          <span>Reset</span>
        </button>
      </div>

      {/* ── Toast Notification ────────────────────────────────────────────── */}
      {toastMessage && (
        <div className="absolute bottom-5 left-5 z-[1000] bg-slate-900/95 backdrop-blur-md border border-teal-500/40 text-teal-300 px-3.5 py-2 rounded-xl text-xs font-mono shadow-2xl flex items-center gap-2 animate-fadeIn">
          <Crosshair className="w-3.5 h-3.5 text-teal-400 shrink-0 animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ── Leaflet Map DOM Container ─────────────────────────────────────── */}
      <div ref={mapContainerRef} className="w-full h-full flex-1 z-0" />
    </div>
  );
};
