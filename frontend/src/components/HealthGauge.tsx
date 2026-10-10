import React from "react";

interface HealthGaugeProps {
  score: number | null;
  grade?: string | null;
  ndviDelta?: number | null;
  ndwiDelta?: number | null;
  status?: string | null;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({
  score = 0,
  grade = "N/A",
  ndviDelta = 0,
  ndwiDelta = 0,
  status = "inconclusive",
}) => {
  const safeScore = Math.max(0, Math.min(100, Math.round(score ?? 0)));

  // Color by score using palette
  let strokeColor = "#3B82C8"; // sentinel
  let gradeBg = "bg-sentinel-faint text-sentinel border-sentinel/20";

  if (safeScore >= 80) {
    strokeColor = "#4D8B31"; // canopy
    gradeBg = "bg-canopy-faint text-canopy border-canopy/20";
  } else if (safeScore >= 65) {
    strokeColor = "#1A6B5A"; // reservoir
    gradeBg = "bg-reservoir-faint text-reservoir border-reservoir/20";
  } else if (safeScore >= 50) {
    strokeColor = "#C4956A"; // alluvial
    gradeBg = "bg-alluvial-faint text-alluvial border-alluvial/20";
  } else {
    strokeColor = "#C44536"; // danger
    gradeBg = "bg-danger-faint text-danger border-danger/20";
  }

  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75;
  const strokeDashoffset = arcLength - (arcLength * safeScore) / 100;

  return (
    <div className="flex flex-col items-center">
      {/* Radial Gauge */}
      <div className="relative w-36 h-36 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-135" viewBox="0 0 130 130">
          <circle
            cx="65"
            cy="65"
            r={radius}
            stroke="var(--color-strata-mid)"
            strokeWidth="10"
            fill="transparent"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          <circle
            cx="65"
            cy="65"
            r={radius}
            stroke={strokeColor}
            strokeWidth="10"
            fill="transparent"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset 1s ease-in-out, stroke 0.5s ease",
            }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
          <div className="text-3xl font-heading font-bold text-basalt tabular-nums">
            {safeScore}
          </div>
          <div className="text-[10px] font-medium text-basalt-light/50">
            Health Score
          </div>
        </div>

        <div
          className={`absolute bottom-0 right-2 px-2 py-0.5 rounded text-[11px] font-heading font-semibold border ${gradeBg}`}
        >
          {grade || "?"}
        </div>
      </div>

      {/* Deltas */}
      <div className="w-full grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-strata-mid text-[12px]">
        <div className="bg-strata/50 rounded p-1.5 border border-strata-mid">
          <div className="text-[10px] text-basalt-light/50 font-medium">Δ NDVI</div>
          <div
            className={`font-semibold tabular-nums ${
              (ndviDelta ?? 0) >= 0 ? "text-canopy" : "text-danger"
            }`}
          >
            {(ndviDelta ?? 0) >= 0 ? "+" : ""}
            {(ndviDelta ?? 0).toFixed(3)}
          </div>
        </div>

        <div className="bg-strata/50 rounded p-1.5 border border-strata-mid">
          <div className="text-[10px] text-basalt-light/50 font-medium">Δ NDWI</div>
          <div
            className={`font-semibold tabular-nums ${
              (ndwiDelta ?? 0) >= 0 ? "text-sentinel" : "text-danger"
            }`}
          >
            {(ndwiDelta ?? 0) >= 0 ? "+" : ""}
            {(ndwiDelta ?? 0).toFixed(3)}
          </div>
        </div>
      </div>
    </div>
  );
};
