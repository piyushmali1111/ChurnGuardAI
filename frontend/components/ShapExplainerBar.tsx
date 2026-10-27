"use client";

import { ShapFactor } from "../lib/types";

interface ShapExplainerBarProps {
  factors: ShapFactor[];
  baseScore?: number;
  score?: number;
}

export function ShapExplainerBar({ factors, baseScore, score }: ShapExplainerBarProps) {
  if (!factors || factors.length === 0) {
    return <div className="text-xs text-ink-muted italic">No SHAP factor data available.</div>;
  }

  // Calculate max absolute points for bar track scaling
  const maxAbsPoints = Math.max(
    ...factors.map((f) => {
      const p = f.points !== undefined ? f.points : f.impact ?? 0;
      return Math.abs(p);
    }),
    1
  );

  return (
    <div className="space-y-4">
      {factors.map((item, idx) => {
        const rawPoints = item.points !== undefined ? item.points : item.impact ?? 0;
        const pts = Math.round(rawPoints);
        const isRiskIncrease = pts > 0;
        const widthPercent = Math.min(Math.round((Math.abs(rawPoints) / maxAbsPoints) * 100), 100);
        const label = item.label || item.factor || item.feature || "Factor";
        const valText = item.value || item.description || "";

        return (
          <div key={item.feature || item.factor || idx} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-ink">{label}</span>
                {valText && (
                  <span className="text-[11px] font-mono text-ink-muted bg-paper px-1.5 py-0.5 rounded case-border">
                    {valText}
                  </span>
                )}
              </div>
              <span
                className={`font-mono font-bold ${
                  isRiskIncrease ? "text-rose" : "text-teal"
                }`}
              >
                {isRiskIncrease ? `+${pts} pts` : `${pts} pts`}
              </span>
            </div>

            {/* Horizontal Bar Track */}
            <div className="h-2.5 w-full bg-paper case-border rounded-none overflow-hidden relative">
              <div
                className={`h-full transition-all duration-500 ${
                  isRiskIncrease ? "bg-rose/85" : "bg-teal/85"
                }`}
                style={{ width: `${Math.max(widthPercent, 2)}%` }}
              />
            </div>
          </div>
        );
      })}

      {/* Footer Line per Section 6 */}
      {baseScore !== undefined && score !== undefined && (
        <div className="pt-3 case-border-t flex items-center justify-between text-xs font-mono text-ink">
          <span className="text-ink-muted">Model Baseline Trajectory:</span>
          <span className="font-bold">
            Base risk {Math.round(baseScore)} → This customer {Math.round(score)}
          </span>
        </div>
      )}
    </div>
  );
}
