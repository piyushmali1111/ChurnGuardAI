"use client";

import { DashboardSummary } from "../lib/types";

interface TopMetricsStripProps {
  summary: DashboardSummary | null;
  loading?: boolean;
}

export function TopMetricsStrip({ summary, loading }: TopMetricsStripProps) {
  if (loading || !summary) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 case-border bg-white rounded-sm overflow-hidden mb-8">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="p-5 case-border-r case-border-b lg:case-border-b-0 animate-pulse">
            <div className="h-4 bg-line/60 rounded w-24 mb-3"></div>
            <div className="h-8 bg-line/60 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  const threshold = summary.risk_threshold ?? 60;
  const delta = summary.retention_delta_vs_last_month !== undefined ? summary.retention_delta_vs_last_month : 0;
  const deltaStr = `${delta >= 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`} vs last month`;

  const metrics = [
    {
      label: "TOTAL CUSTOMERS",
      value: summary.total_customers.toLocaleString(),
      subtext: "Active in database",
      color: "text-ink",
      tooltip: "Total count of active customer accounts tracked by ChurnGuardAI",
    },
    {
      label: "FLAGGED HIGH-RISK TODAY",
      value: summary.high_risk_today.toLocaleString(),
      subtext: `Score >= ${threshold} threshold`,
      color: "text-amber",
      tooltip: `Customers with churn risk score at or above the ${threshold} business threshold`,
    },
    {
      label: "RETENTION RATE (30D)",
      value: `${summary.retention_rate_30d}%`,
      subtext: deltaStr,
      color: "text-teal",
      tooltip: "Retained customers / (retained + churned) over the last 30 days. Retained: placed order or accepted offer in window; Churned: inactive high-risk in window.",
    },
    {
      label: "OFFERS PENDING APPROVAL",
      value: summary.pending_offers_count,
      subtext: "Requires human review",
      color: summary.pending_offers_count > 0 ? "text-amber font-bold" : "text-ink",
      tooltip: "AI-drafted retention offers awaiting human approval in the Approval Inbox",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 case-border bg-white rounded-sm overflow-hidden mb-8 shadow-none">
      {metrics.map((item, idx) => (
        <div
          key={item.label}
          title={item.tooltip}
          className={`p-5 flex flex-col justify-between ${
            idx < 3 ? "case-border-r" : ""
          } ${idx < 2 ? "case-border-b lg:case-border-b-0" : ""}`}
        >
          <span className="text-[11px] font-semibold tracking-wider text-ink-muted uppercase font-mono">
            {item.label}
          </span>
          <div className="my-2">
            <span className={`text-3xl font-bold tracking-tight font-mono ${item.color}`}>
              {item.value}
            </span>
          </div>
          <span className="text-xs text-ink-muted/80 font-mono">{item.subtext}</span>
        </div>
      ))}
    </div>
  );
}
