"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TopMetricsStrip } from "../components/TopMetricsStrip";
import { DashboardSummary, Offer } from "../lib/types";
import { api } from "../lib/api";
import { ArrowRight, Inbox, RefreshCw, AlertCircle, CheckCircle } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

// Section 10: Custom Tooltip showing Week, Retained, Churned, Retention rate %
const CohortTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const rate =
      data.retention_rate !== undefined
        ? data.retention_rate
        : Math.round((data.retained / (data.retained + data.churned)) * 1000) / 10;
    return (
      <div className="bg-[#14213D] text-[#FAF7F3] p-3 rounded-sm border border-[#E3DDD3] text-xs font-mono shadow-md space-y-1">
        <p className="font-bold border-b border-[#FAF7F3]/20 pb-1">Cohort Week: {label}</p>
        <p className="text-[#1F9D82]">Retained: {data.retained.toLocaleString()} customers</p>
        <p className="text-[#D14D4D]">Churned: {data.churned.toLocaleString()} customers</p>
        <p className="text-amber font-semibold pt-1 border-t border-[#FAF7F3]/10">
          Retention Rate: {rate}%
        </p>
      </div>
    );
  }
  return null;
};

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [pendingOffers, setPendingOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const sum = await api.getDashboardSummary();
      const offers = await api.getPendingOffers();
      setSummary(sum);
      setPendingOffers(offers.slice(0, 5));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunScan = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const res = await api.runScan();
      setScanMessage(`Batch scan complete! Generated ${res.new_offers_count} new retention offer(s).`);
      await loadData();
    } catch (err) {
      setScanMessage("Proactive scan failed.");
    } finally {
      setScanning(false);
    }
  };

  const pendingCount = summary?.pending_offers_count ?? pendingOffers.length;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 case-border-b">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
            Operations & Retention Overview
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Real-time churn risk detection and human-in-the-loop offer approvals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunScan}
            disabled={scanning}
            className="px-4 py-2 bg-ink text-paper text-xs font-semibold rounded-sm case-border hover:bg-ink/90 transition-all flex items-center gap-2 disabled:opacity-50 font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanning ? "animate-spin text-amber" : ""}`} />
            <span>{scanning ? "Running AI Batch Scan..." : "Run Proactive Scan"}</span>
          </button>
        </div>
      </div>

      {scanMessage && (
        <div className="p-3 case-border bg-teal/10 border-teal/30 text-teal text-xs font-medium rounded flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span>{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="text-ink-muted hover:text-ink">
            Dismiss
          </button>
        </div>
      )}

      {/* Top Mono Metrics Strip */}
      <TopMetricsStrip summary={summary} loading={loading} />

      {/* Main Grid: Chart (Left 2 cols) & Needs Attention (Right 1 col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Retention vs Churn Trend Chart (Section 10: Dual Y-axis, all 8 weeks interval=0) */}
        <div className="lg:col-span-2 case-border bg-white rounded-sm p-6">
          <div className="flex items-center justify-between mb-6 pb-3 case-border-b">
            <div>
              <h2 className="font-display font-bold text-lg tracking-tight text-ink">
                Customer Cohort Performance
              </h2>
              <p className="text-xs text-ink-muted">
                8-week trend of retained customers vs. churned customers (W1 to W8)
              </p>
            </div>
            <span className="text-xs text-ink-muted bg-paper px-2.5 py-1 case-border rounded font-mono">
              Weekly Cohorts
            </span>
          </div>

          <div className="h-72 w-full">
            {summary?.weekly_trend ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={summary.weekly_trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E3DDD3" vertical={false} />
                  <XAxis dataKey="week" interval={0} stroke="#5B6472" fontSize={11} tickLine={false} />
                  {/* Left Axis: Retained Customers */}
                  <YAxis yAxisId="left" stroke="#1F9D82" fontSize={11} tickLine={false} />
                  {/* Right Axis: Churned Customers */}
                  <YAxis yAxisId="right" orientation="right" stroke="#D14D4D" fontSize={11} tickLine={false} />
                  <Tooltip content={<CohortTooltip />} />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="retained"
                    name="Retained Customers (Left Axis)"
                    stroke="#1F9D82"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#1F9D82" }}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="churned"
                    name="Churned Customers (Right Axis)"
                    stroke="#D14D4D"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={{ r: 3, fill: "#D14D4D" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-ink-muted font-mono">
                Loading retention chart...
              </div>
            )}
          </div>
        </div>

        {/* Needs Your Attention Widget */}
        <div className="case-border bg-white rounded-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 case-border-b">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber" />
                <h2 className="font-display font-bold text-base tracking-tight text-ink">
                  Needs Your Attention
                </h2>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 bg-amber/20 text-ink rounded-full font-mono">
                {pendingCount} Pending
              </span>
            </div>

            {pendingOffers.length === 0 ? (
              <div className="py-12 text-center space-y-2">
                <p className="text-xs text-ink-muted">All drafted offers have been reviewed!</p>
                <p className="text-[11px] text-ink-muted/80">
                  New offers will appear when high-risk churn patterns or angry tickets are detected.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingOffers.map((offer) => (
                  <div
                    key={offer.id}
                    className="p-3 case-border risk-accent-amber bg-paper/40 rounded-sm space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-semibold text-ink">
                        {offer.customer_name || offer.customer_id}
                      </span>
                      <span className="text-amber font-bold">{offer.discount_percent}% Off</span>
                    </div>

                    <p className="text-ink-muted line-clamp-2 leading-relaxed">
                      &quot;{offer.drafted_message}&quot;
                    </p>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] font-mono text-ink-muted/80">
                        {offer.ticket_id ? `Ticket ${offer.ticket_id}` : "Proactive Scan"}
                      </span>
                      <Link
                        href="/approvals"
                        className="text-[11px] font-mono font-medium text-ink hover:text-amber flex items-center gap-1"
                      >
                        Review Offer <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="pt-4 mt-4 case-border-t">
            <Link
              href="/approvals"
              className="w-full py-2 bg-paper case-border text-ink hover:bg-ink hover:text-paper text-xs font-mono font-semibold rounded-sm transition-colors flex items-center justify-center gap-2"
            >
              <Inbox className="w-3.5 h-3.5" />
              <span>Go to Approval Inbox ({pendingCount})</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
