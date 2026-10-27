"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useOffersStore } from "../../lib/store";
import { AgentActivityWidget } from "../../components/AgentActivityWidget";
import { Offer } from "../../lib/types";
import { api } from "../../lib/api";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Edit3,
  Save,
  ShieldCheck,
  Bot,
  Percent,
  Sparkles,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

export default function ApprovalInboxPage() {
  const { offers, isLoading, fetchPendingOffers, approveOffer, rejectOffer, updateOffer } =
    useOffersStore();

  const [editingOfferId, setEditingOfferId] = useState<string | null>(null);
  const [editMessage, setEditMessage] = useState<string>("");
  const [editDiscount, setEditDiscount] = useState<number>(20);
  const [maxDiscount, setMaxDiscount] = useState<number>(25);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchPendingOffers();
    async function loadSettings() {
      try {
        const s = await api.getSettings();
        if (s?.max_discount_percent) {
          setMaxDiscount(s.max_discount_percent);
        }
      } catch (err) {
        console.error("Failed to load settings:", err);
      }
    }
    loadSettings();
  }, [fetchPendingOffers]);

  const handleStartEdit = (offer: Offer) => {
    setEditingOfferId(offer.id);
    setEditMessage(offer.drafted_message);
    setEditDiscount(offer.discount_percent);
  };

  const handleSaveEdit = async (offerId: string) => {
    try {
      await updateOffer(offerId, editMessage, editDiscount);
      setEditingOfferId(null);
      setActionSuccess("Offer changes saved successfully!");
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err) {
      alert("Failed to save offer edits.");
    }
  };

  const handleApprove = async (id: string, name?: string) => {
    try {
      await approveOffer(id);
      setActionSuccess(`Approved & sent retention offer to ${name || "customer"}!`);
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err) {
      alert("Failed to approve offer.");
    }
  };

  const handleReject = async (id: string, name?: string) => {
    try {
      await rejectOffer(id);
      setActionSuccess(`Rejected retention offer for ${name || "customer"}.`);
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err) {
      alert("Failed to reject offer.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 case-border-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
              Human-in-the-Loop Approval Inbox
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-amber text-ink rounded-full">
              {offers.length} Pending
            </span>
          </div>
          <p className="text-sm text-ink-muted mt-1">
            Review, edit, approve, or reject retention offers drafted by the AI agent swarm.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-ink-muted bg-paper p-2 rounded case-border">
          <ShieldCheck className="w-4 h-4 text-teal" />
          <span>Verifier Guard: Max {maxDiscount}% Discount Ceiling</span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3 case-border bg-teal/10 border-teal/40 text-teal text-xs font-medium rounded flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-ink-muted hover:text-ink">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Pending Offers List (Left 8 cols) & Live Agent Stream (Right 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Offers List */}
        <div className="lg:col-span-8 space-y-6">
          {isLoading ? (
            <div className="case-border bg-white p-12 rounded-sm text-center text-xs font-mono text-ink-muted">
              Loading pending retention offers...
            </div>
          ) : offers.length === 0 ? (
            <div className="case-border bg-white p-12 rounded-sm text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-teal/10 text-teal flex items-center justify-center mx-auto case-border border-teal/30">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="font-display font-bold text-lg tracking-tight text-ink">
                All Pending Offers Reviewed!
              </h3>
              <p className="text-xs text-ink-muted max-w-md mx-auto leading-relaxed">
                There are currently no AI-drafted retention offers waiting for human review. Run a proactive batch scan or submit a support ticket to trigger new agent drafts.
              </p>
              <div className="pt-2">
                <Link
                  href="/"
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink text-paper text-xs font-mono font-medium rounded-sm"
                >
                  Return to Dashboard
                </Link>
              </div>
            </div>
          ) : (
            offers.map((offer) => {
              const isEditing = editingOfferId === offer.id;

              return (
                <div
                  key={offer.id}
                  className="case-border bg-white rounded-sm p-6 space-y-4 risk-accent-amber hover:border-ink/30 transition-colors"
                >
                  {/* Top Bar: Customer Info + Risk Badge */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 case-border-b">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/customers/${offer.customer_id}`}
                          className="font-display font-bold text-lg text-ink hover:underline tracking-tight"
                        >
                          {offer.customer_name || offer.customer_id}
                        </Link>
                        <span className="text-xs font-mono text-ink-muted">
                          ID: {offer.customer_id}
                        </span>
                      </div>
                      {/* Compact line under customer name per Section 5 */}
                      <div className="text-xs font-mono text-ink-muted">
                        Baseline {offer.baseline_score ?? "—"} · Urgency {offer.urgency_score ?? "—"} · Fused {offer.fused_score ?? "—"}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 bg-amber/15 text-amber text-xs font-mono font-bold rounded case-border">
                        Proposed Discount: {offer.discount_percent}%
                      </span>
                      {offer.ticket_id && (
                        <span className="px-2 py-1 bg-paper text-ink-muted text-[11px] font-mono case-border">
                          Ticket {offer.ticket_id}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Agent Reasoning Note */}
                  <div className="p-3 case-border bg-paper/60 rounded-sm text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-mono text-[11px] text-ink font-semibold">
                      <Bot className="w-3.5 h-3.5 text-amber" />
                      <span>Retention Agent Reasoning:</span>
                    </div>
                    <p className="text-ink-muted italic leading-relaxed">
                      &quot;{offer.reasoning}&quot;
                    </p>
                  </div>

                  {/* Drafted Message Content / Text Area */}
                  <div>
                    <label className="block text-[11px] font-mono font-semibold text-ink uppercase mb-1">
                      Drafted Retention Offer Message {isEditing && "(Editing)"}
                    </label>

                    {isEditing ? (
                      <div className="space-y-3">
                        <textarea
                          rows={3}
                          value={editMessage}
                          onChange={(e) => setEditMessage(e.target.value)}
                          className="w-full p-3 text-xs case-border rounded bg-paper text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                        />

                        <div className="flex items-center gap-4">
                          <label className="text-xs font-mono text-ink">
                            Discount Percent:
                          </label>
                          <input
                            type="number"
                            min={5}
                            max={maxDiscount}
                            value={editDiscount}
                            onChange={(e) => setEditDiscount(Number(e.target.value))}
                            className="w-20 p-1 text-xs font-mono case-border rounded bg-paper text-ink"
                          />
                          <span className="text-[11px] text-ink-muted font-mono">
                            (Max allowed by Verifier: {maxDiscount}%)
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3.5 case-border bg-white rounded-sm text-xs text-ink leading-relaxed font-sans">
                        &quot;{offer.drafted_message}&quot;
                      </div>
                    )}
                  </div>

                  {/* Action Buttons Bar */}
                  <div className="pt-3 case-border-t flex flex-wrap items-center justify-between gap-3">
                    <div className="text-[11px] font-mono text-ink-muted">
                      Created: {new Date(offer.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>

                    <div className="flex items-center gap-2">
                      {isEditing ? (
                        <button
                          onClick={() => handleSaveEdit(offer.id)}
                          className="px-3 py-1.5 bg-ink text-paper text-xs font-mono font-semibold rounded-sm hover:bg-ink/90 flex items-center gap-1.5"
                        >
                          <Save className="w-3.5 h-3.5 text-amber" /> Save Edits
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(offer)}
                          className="px-3 py-1.5 bg-paper case-border text-ink text-xs font-mono font-medium rounded-sm hover:bg-line transition-colors flex items-center gap-1.5"
                        >
                          <Edit3 className="w-3.5 h-3.5" /> Edit Offer
                        </button>
                      )}

                      <button
                        onClick={() => handleReject(offer.id, offer.customer_name)}
                        className="px-3 py-1.5 bg-rose/10 text-rose case-border border-rose/30 text-xs font-mono font-semibold rounded-sm hover:bg-rose/20 transition-colors flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Reject
                      </button>

                      <button
                        onClick={() => handleApprove(offer.id, offer.customer_name)}
                        className="px-4 py-1.5 bg-teal text-paper text-xs font-mono font-bold rounded-sm hover:bg-teal/90 transition-colors flex items-center gap-1.5 shadow-sm"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Approve & Dispatch
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Live Agent Swarm Stream */}
        <div className="lg:col-span-4 space-y-6">
          <AgentActivityWidget />
        </div>
      </div>
    </div>
  );
}
