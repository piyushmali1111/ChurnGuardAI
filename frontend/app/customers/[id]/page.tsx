"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { CustomerDetail } from "../../../lib/types";
import { api } from "../../../lib/api";
import { formatCurrency, formatRecency, getInitials } from "../../../lib/formatters";
import { ShapExplainerBar } from "../../../components/ShapExplainerBar";
import {
  ArrowLeft,
  Calendar,
  CreditCard,
  ShoppingBag,
  Ticket as TicketIcon,
  Gift,
  AlertTriangle,
  UserCheck,
  ShieldAlert,
} from "lucide-react";

export default function CustomerDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [threshold, setThreshold] = useState<number>(60);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [custData, settingsData] = await Promise.all([
          api.getCustomerById(resolvedParams.id),
          api.getSettings().catch(() => null),
        ]);
        setCustomer(custData);
        if (settingsData?.risk_threshold) {
          setThreshold(settingsData.risk_threshold);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [resolvedParams.id]);

  if (loading) {
    return (
      <div className="py-16 text-center text-xs text-ink-muted font-mono">
        Loading customer case file #{resolvedParams.id}...
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="py-16 text-center space-y-4">
        <p className="text-sm text-ink-muted">Customer record #{resolvedParams.id} not found.</p>
        <Link href="/customers" className="text-xs font-mono text-ink underline">
          Return to Customer Directory
        </Link>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= threshold) return { text: "text-rose", border: "border-rose", bg: "bg-rose/10" };
    if (score >= threshold - 20) return { text: "text-amber", border: "border-amber", bg: "bg-amber/10" };
    return { text: "text-teal", border: "border-teal", bg: "bg-teal/10" };
  };

  const scoreTheme = getScoreColor(customer.churn_risk_score);
  const initials = getInitials(customer.name);

  return (
    <div className="space-y-8">
      {/* Back Button & Header */}
      <div>
        <Link
          href="/customers"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-ink-muted hover:text-ink mb-4 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Customers Table
        </Link>

        {/* Profile Card Header */}
        <div className="case-border bg-white rounded-sm p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-paper case-border flex items-center justify-center font-display font-bold text-base text-ink shrink-0">
              {initials}
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">{customer.name}</h1>
                <span
                  className={`px-3 py-1 text-xs font-semibold rounded-full ${
                    customer.churn_status === "High Risk"
                      ? "bg-rose/20 text-rose"
                      : customer.churn_status === "Watching"
                      ? "bg-amber/20 text-amber"
                      : "bg-teal/20 text-teal"
                  }`}
                >
                  {customer.churn_status}
                </span>
              </div>
              <p className="text-xs text-ink-muted font-mono">
                ID: <span className="font-semibold text-ink">{customer.id}</span> • {customer.email}
              </p>
            </div>
          </div>

          {/* Core Customer Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs case-border p-4 bg-paper/60 rounded-sm">
            <div>
              <span className="text-ink-muted block text-[10px] uppercase font-mono">Lifetime Value</span>
              <span className="font-bold text-ink text-sm font-mono">{formatCurrency(customer.total_spent)}</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase font-mono">Orders Count</span>
              <span className="font-bold text-ink text-sm font-mono">{customer.order_count} purchases</span>
            </div>
            <div>
              <span className="text-ink-muted block text-[10px] uppercase font-mono">Last Order Date</span>
              <span className="font-bold text-ink text-sm font-mono">
                {customer.last_order_date} ({formatRecency(customer.last_order_date)})
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Score & SHAP Breakdown (Left 7 cols) & History Timeline (Right 5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Risk Score Gauge + SHAP Factors */}
        <div className="lg:col-span-7 space-y-6">
          {/* Churn Risk Score Box */}
          <div className="case-border bg-white rounded-sm p-6">
            <div className="flex items-center justify-between pb-4 case-border-b mb-6">
              <h2 className="font-display font-bold text-lg tracking-tight text-ink">
                AI Churn Risk Score Assessment
              </h2>
              <span className="text-xs font-mono text-ink-muted">
                XGBoost + SHAP Model
              </span>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-6">
              {/* Mono Score Ring Gauge */}
              <div
                className={`w-32 h-32 rounded-full border-4 ${scoreTheme.border} ${scoreTheme.bg} flex flex-col items-center justify-center shrink-0 shadow-none`}
              >
                <span className={`text-4xl font-mono font-bold ${scoreTheme.text}`}>
                  {customer.churn_risk_score}
                </span>
                <span className="text-[10px] font-mono text-ink-muted uppercase tracking-wider">
                  Out of 100
                </span>
              </div>

              <div className="space-y-2 text-xs leading-relaxed text-ink-muted flex-1">
                <p className="font-semibold text-ink">
                  Risk Level: {customer.churn_status}
                </p>
                <p>
                  Scores above {threshold} auto-trigger the Retention Agent to draft customized discount offers for human approval.
                </p>

                {/* Section 5: Fused Risk Score Callout */}
                {customer.fused_score !== undefined && customer.urgency_score !== null && customer.urgency_score !== undefined && (
                  <div className="p-2 case-border rounded bg-purple-50/80 text-purple-900 font-mono text-xs font-semibold">
                    Latest fused score: {customer.fused_score} (baseline {customer.baseline_score ?? customer.churn_risk_score}, urgency {customer.urgency_score})
                  </div>
                )}

                <div className="pt-1 flex items-center gap-4 text-[11px] font-mono">
                  <span>Satisfaction: {customer.satisfaction_score}/5.0</span>
                  <span>Complaints: {customer.complaint_count}</span>
                </div>
              </div>
            </div>
          </div>

          {/* "Why this score" SHAP Breakdown */}
          <div className="case-border bg-white rounded-sm p-6">
            <div className="pb-4 case-border-b mb-6 flex items-center justify-between">
              <div>
                <h3 className="font-display font-bold text-lg tracking-tight text-ink">
                  Why is this customer at risk?
                </h3>
                <p className="text-xs text-ink-muted">
                  SHAP feature attribution points driving the model&apos;s score output
                </p>
              </div>
              <span className="text-xs font-mono text-ink-muted bg-paper px-2 py-1 case-border">
                Explainable AI
              </span>
            </div>

            <ShapExplainerBar
              factors={customer.shap_factors}
              baseScore={customer.base_score}
              score={customer.churn_risk_score}
            />
          </div>
        </div>

        {/* Right Column: Ticket History & Offer Timeline */}
        <div className="lg:col-span-5 space-y-6">
          {/* Retention Offer Status */}
          <div className="case-border bg-white rounded-sm p-6">
            <div className="flex items-center justify-between pb-3 mb-4 case-border-b">
              <div className="flex items-center gap-2">
                <Gift className="w-4 h-4 text-amber" />
                <h3 className="font-display font-bold text-base tracking-tight text-ink">
                  Retention Offers History
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-muted">
                {customer.offers.length} Offer(s)
              </span>
            </div>

            {customer.offers.length === 0 ? (
              <p className="text-xs text-ink-muted italic py-4">
                No retention offers drafted for this customer yet.
              </p>
            ) : (
              <div className="space-y-3">
                {customer.offers.map((offer) => (
                  <div
                    key={offer.id}
                    className="p-3.5 case-border bg-paper/60 rounded-sm space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-bold text-ink">{offer.discount_percent}% Discount</span>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                          offer.status === "Approved"
                            ? "bg-teal/20 text-teal"
                            : offer.status === "Pending"
                            ? "bg-amber/20 text-amber"
                            : "bg-rose/20 text-rose"
                        }`}
                      >
                        {offer.status}
                      </span>
                    </div>
                    {offer.fused_score !== undefined && (
                      <p className="text-[11px] font-mono text-purple-800 font-semibold">
                        Baseline {offer.baseline_score ?? "N/A"} · Urgency {offer.urgency_score ?? "N/A"} · Fused {offer.fused_score}
                      </p>
                    )}
                    <p className="text-ink-muted leading-relaxed font-sans">
                      &quot;{offer.drafted_message}&quot;
                    </p>
                    <p className="text-[11px] font-mono text-ink-muted/80">
                      Reasoning: {offer.reasoning}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Ticket History Timeline */}
          <div className="case-border bg-white rounded-sm p-6">
            <div className="flex items-center justify-between pb-3 mb-4 case-border-b">
              <div className="flex items-center gap-2">
                <TicketIcon className="w-4 h-4 text-ink" />
                <h3 className="font-display font-bold text-base tracking-tight text-ink">
                  Support Ticket Timeline
                </h3>
              </div>
              <span className="text-xs font-mono text-ink-muted">
                {customer.ticket_history.length} Ticket(s)
              </span>
            </div>

            {customer.ticket_history.length === 0 ? (
              <p className="text-xs text-ink-muted italic py-4">
                No support tickets filed by this customer.
              </p>
            ) : (
              <div className="space-y-4">
                {customer.ticket_history.map((ticket) => (
                  <div key={ticket.id} className="case-border p-3 rounded-sm bg-paper/30 space-y-2 text-xs">
                    <div className="flex items-center justify-between font-mono text-[11px]">
                      <span className="font-bold text-ink">#{ticket.id}</span>
                      <span className="text-ink-muted">
                        {new Date(ticket.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {ticket.fused_score !== undefined && (
                      <div className="text-[11px] font-mono text-purple-800">
                        Baseline {ticket.baseline_score ?? "N/A"} · Urgency {ticket.urgency_score ?? "N/A"} · Fused {ticket.fused_score}
                      </div>
                    )}
                    <p className="text-ink-muted font-sans">&quot;{ticket.message}&quot;</p>
                    {ticket.agent_reply && (
                      <div className="pt-2 case-border-t text-[11px] text-ink font-sans">
                        <span className="font-bold font-mono">Agent Reply:</span> {ticket.agent_reply}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
