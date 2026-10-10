"use client";

import React, { useState, useEffect, useRef } from "react";
import { Search, X, MapPin, Loader2, Navigation } from "lucide-react";

export interface GeocodedLocation {
  name: string;
  displayName: string;
  lat: number;
  lon: number;
  type?: string;
}

interface LocationSearchInputProps {
  onLocationSelect: (location: GeocodedLocation) => void;
  placeholder?: string;
  className?: string;
  initialQuery?: string;
}

export const LocationSearchInput: React.FC<LocationSearchInputProps> = ({
  onLocationSelect,
  placeholder = "Search city, village, river, watershed, or coordinates...",
  className = "",
  initialQuery = "",
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<GeocodedLocation[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [statusNote, setStatusNote] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Synchronize internal query state when initialQuery changes externally
  useEffect(() => {
    if (initialQuery !== undefined) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  // Debounced geocoding search using Nominatim
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed || trimmed.length < 2) {
      setResults([]);
      setIsSearching(false);
      return;
    }

    // Direct coordinate match (e.g. "18.52, 73.85" or "18.5204 73.8567")
    const coordMatch = trimmed.match(/^([-+]?\d{1,2}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$/);
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1]);
      const lon = parseFloat(coordMatch[2]);
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        setResults([
          {
            name: `Coordinates (${lat.toFixed(4)}°, ${lon.toFixed(4)}°)`,
            displayName: `Direct Coordinates: ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
            lat,
            lon,
            type: "coordinate",
          },
        ]);
        setIsDropdownOpen(true);
        setIsSearching(false);
        return;
      }
    }

    setIsSearching(true);
    const timeoutId = setTimeout(async () => {
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          trimmed
        )}&limit=6&addressdetails=1`;
        const res = await fetch(url, {
          headers: {
            "Accept-Language": "en",
          },
        });
        if (!res.ok) throw new Error("Geocoding failed");
        const data = await res.json();
        const formatted: GeocodedLocation[] = data.map((item: any) => ({
          name: item.display_name.split(",")[0],
          displayName: item.display_name,
          lat: parseFloat(item.lat),
          lon: parseFloat(item.lon),
          type: item.type || item.class,
        }));
        setResults(formatted);
        setIsDropdownOpen(true);
      } catch (err) {
        console.warn("Geocoding search error:", err);
      } finally {
        setIsSearching(false);
      }
    }, 350);

    return () => clearTimeout(timeoutId);
  }, [query]);

  const handleSelect = (loc: GeocodedLocation) => {
    setQuery(loc.name);
    setIsDropdownOpen(false);
    onLocationSelect(loc);
  };

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (results.length > 0) {
        handleSelect(results[0]);
      } else if (query.trim().length >= 2) {
        setIsSearching(true);
        try {
          const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
            query.trim()
          )}&limit=1&addressdetails=1`;
          const res = await fetch(url, {
            headers: { "Accept-Language": "en" },
          });
          if (res.ok) {
            const data = await res.json();
            if (data.length > 0) {
              const item = data[0];
              const loc: GeocodedLocation = {
                name: item.display_name.split(",")[0],
                displayName: item.display_name,
                lat: parseFloat(item.lat),
                lon: parseFloat(item.lon),
                type: item.type || item.class,
              };
              handleSelect(loc);
            }
          }
        } catch (err) {
          console.warn("Direct geocode search error:", err);
        } finally {
          setIsSearching(false);
        }
      }
    }
  };

  // Browser Geolocation
  const handleLocateMe = () => {
    if (!navigator.geolocation) {
      setStatusNote("Geolocation not supported by browser");
      return;
    }
    setIsLocating(true);
    setStatusNote(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setIsLocating(false);
        const lat = Number(pos.coords.latitude.toFixed(4));
        const lon = Number(pos.coords.longitude.toFixed(4));
        // Reverse geocode to find place name
        try {
          const revRes = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`
          );
          const revData = await revRes.json();
          const placeName = revData.display_name?.split(",")[0] || `Location (${lat}, ${lon})`;
          const loc: GeocodedLocation = {
            name: placeName,
            displayName: revData.display_name || `${lat}°N, ${lon}°E`,
            lat,
            lon,
            type: "current_position",
          };
          setQuery(placeName);
          onLocationSelect(loc);
        } catch {
          const loc: GeocodedLocation = {
            name: `Current Position (${lat}, ${lon})`,
            displayName: `Current Position: ${lat}°N, ${lon}°E`,
            lat,
            lon,
            type: "current_position",
          };
          setQuery(loc.name);
          onLocationSelect(loc);
        }
      },
      (err) => {
        setIsLocating(false);
        setStatusNote(`Location error: ${err.message}`);
        setTimeout(() => setStatusNote(null), 3000);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  return (
    <div className={`relative w-full ${className}`} ref={dropdownRef}>
      <div className="relative flex items-center">
        <div className="absolute left-3 text-teal-600 pointer-events-none">
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
          ) : (
            <Search className="w-4 h-4" />
          )}
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (results.length > 0) setIsDropdownOpen(true);
          }}
          placeholder={placeholder}
          className="w-full pl-9 pr-18 py-2.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-500/10 shadow-xs transition-all font-medium"
        />

        <div className="absolute right-2 flex items-center gap-1">
          {query && (
            <button
              onClick={() => {
                setQuery("");
                setResults([]);
                setIsDropdownOpen(false);
              }}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={handleLocateMe}
            disabled={isLocating}
            className="p-1.5 text-teal-600 hover:text-teal-700 hover:bg-teal-50 rounded-lg transition-all cursor-pointer"
            title="Use current GPS position"
          >
            {isLocating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Navigation className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {statusNote && (
        <div className="text-[11px] text-amber-600 mt-1 pl-1 font-medium">{statusNote}</div>
      )}

      {/* Autocomplete Suggestions Dropdown */}
      {isDropdownOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden z-50 max-h-60 overflow-y-auto">
          {results.map((item, idx) => (
            <button
              key={`${item.lat}-${item.lon}-${idx}`}
              onClick={() => handleSelect(item)}
              className="w-full text-left px-3.5 py-2.5 hover:bg-teal-50/60 border-b border-slate-100 last:border-0 flex items-start gap-2.5 transition-colors cursor-pointer group"
            >
              <MapPin className="w-4 h-4 text-teal-600 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-slate-900 truncate group-hover:text-teal-900">
                  {item.name}
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  {item.displayName}
                </div>
              </div>
              <span className="text-[10px] font-mono text-teal-700 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded-md shrink-0 mt-0.5 font-semibold">
                {item.lat.toFixed(3)}°, {item.lon.toFixed(3)}°
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
