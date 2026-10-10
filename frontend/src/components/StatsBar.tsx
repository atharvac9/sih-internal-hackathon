import React from "react";
import { Site } from "../lib/types";

interface StatsBarProps {
  sites: Site[];
  onSelectAnomaly: () => void;
}

export const StatsBar: React.FC<StatsBarProps> = ({ sites, onSelectAnomaly }) => {
  const totalSites = sites.length;
  const confirmed = sites.filter(
    (s) => s.latest_analysis?.overall_status === "confirmed"
  ).length;
  const anomalies = sites.filter(
    (s) => s.latest_analysis?.overall_status === "anomaly"
  ).length;

  const validScores = sites
    .map((s) => s.latest_analysis?.health_score)
    .filter((score): score is number => score !== null && score !== undefined);

  const avgHealth = validScores.length
    ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
    : null;

  return (
    <div className="flex flex-wrap items-stretch rounded-lg border border-strata-mid bg-surface divide-x divide-strata-mid">
      {/* Sites */}
      <div className="flex-1 min-w-[120px] px-4 py-3 flex items-center gap-3">
        <div className="flex flex-col">
          <span className="text-[11px] text-basalt-light/50 font-medium">Sites</span>
          <span className="text-xl font-heading font-bold text-basalt tabular-nums">{totalSites}</span>
        </div>
      </div>

      {/* Confirmed */}
      <div className="flex-1 min-w-[120px] px-4 py-3 flex items-center gap-3">
        <div className="flex flex-col">
          <span className="text-[11px] text-basalt-light/50 font-medium">Verified</span>
          <span className="text-xl font-heading font-bold text-canopy tabular-nums">{confirmed}</span>
        </div>
      </div>

      {/* Anomalies */}
      <button
        onClick={onSelectAnomaly}
        className={`flex-1 min-w-[120px] px-4 py-3 flex items-center gap-3 transition-colors cursor-pointer ${
          anomalies > 0
            ? "bg-danger-faint hover:bg-danger-faint/80"
            : "hover:bg-strata/30"
        }`}
      >
        <div className="flex flex-col">
          <span className="text-[11px] text-basalt-light/50 font-medium">Anomalies</span>
          <span className={`text-xl font-heading font-bold tabular-nums ${
            anomalies > 0 ? "text-danger" : "text-basalt"
          }`}>
            {anomalies}
          </span>
        </div>
      </button>

      {/* Average Health */}
      <div className="flex-1 min-w-[120px] px-4 py-3 flex items-center gap-3">
        <div className="flex flex-col">
          <span className="text-[11px] text-basalt-light/50 font-medium">Avg. Health</span>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-heading font-bold text-sentinel tabular-nums">
              {avgHealth ?? "—"}
            </span>
            {avgHealth !== null && (
              <span className="text-[11px] text-basalt-light/40 font-body">/100</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
