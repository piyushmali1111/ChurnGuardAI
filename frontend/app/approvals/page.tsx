"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useOffersStore, OfferTabType } from "../../lib/store";
import { AgentActivityWidget } from "../../components/AgentActivityWidget";
import { Offer } from "../../lib/types";
import { api } from "../../lib/api";
import { formatLiveDateTime, formatRelativeTime } from "../../lib/formatters";
import {
  Inbox,
  CheckCircle2,
  XCircle,
  Edit3,
  Save,
  ShieldCheck,
  Bot,
  Clock,
  Send,
  FileText,
} from "lucide-react";

export default function ApprovalInboxPage() {
  const { offers, isLoading, fetchOffers, approveOffer, rejectOffer, updateOffer } =
    useOffersStore();

  const [activeTab, setActiveTab] = useState<OfferTabType>("Pending");
  const [editingOfferId, setEditingOfferId] = useState<string | null>(null);
  const [editMessage, setEditMessage] = useState<string>("");
  const [editDiscount, setEditDiscount] = useState<number>(20);
  const [maxDiscount, setMaxDiscount] = useState<number>(25);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchOffers();
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
  }, [fetchOffers]);

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
      setTimeout(() => setActionSuccess(null), 3500);
    } catch (err) {
      alert("Failed to save offer edits.");
    }
  };

  const handleApprove = async (id: string, name?: string) => {
    try {
      await approveOffer(id);
      setActionSuccess(`Approved & dispatched offer to ${name || "customer"}! View in "Accepted & Dispatched" tab.`);
      setTimeout(() => setActionSuccess(null), 4500);
    } catch (err) {
      alert("Failed to approve offer.");
    }
  };

  const handleReject = async (id: string, name?: string) => {
    try {
      await rejectOffer(id);
      setActionSuccess(`Rejected retention offer for ${name || "customer"}. View in "Rejected Offers" tab.`);
      setTimeout(() => setActionSuccess(null), 4500);
    } catch (err) {
      alert("Failed to reject offer.");
    }
  };

  const pendingOffers = offers.filter((o) => o.status === "Pending" || o.status === "Edited");
  const approvedOffers = offers.filter((o) => o.status === "Approved");
  const rejectedOffers = offers.filter((o) => o.status === "Rejected");

  const displayedOffers =
    activeTab === "Pending"
      ? pendingOffers
      : activeTab === "Approved"
      ? approvedOffers
      : activeTab === "Rejected"
      ? rejectedOffers
      : offers;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 case-border-b">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
              Human-in-the-Loop Approval Inbox
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold bg-amber text-ink rounded-full font-mono">
              {pendingOffers.length} Pending
            </span>
          </div>
          <p className="text-sm text-ink-muted mt-1">
            Review, edit, approve, or reject retention offers drafted by the AI agent swarm.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-ink-muted bg-paper p-2 rounded case-border font-mono">
          <ShieldCheck className="w-4 h-4 text-teal" />
          <span>Verifier Guard: Max {maxDiscount}% Discount Ceiling</span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-3.5 case-border bg-teal/10 border-teal/40 text-teal text-xs font-medium rounded flex items-center justify-between animate-fade-in shadow-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal" />
            <span className="font-sans">{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-ink-muted hover:text-ink text-xs font-mono ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Section Tabs: Pending, Approved, Rejected, All */}
      <div className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
        <button
          onClick={() => setActiveTab("Pending")}
          className={`px-4 py-2 text-xs font-mono font-semibold rounded-sm transition-all flex items-center gap-2 ${
            activeTab === "Pending"
              ? "bg-ink text-paper shadow-sm"
              : "bg-white text-ink-muted hover:text-ink hover:bg-paper case-border"
          }`}
        >
          <Inbox className="w-3.5 h-3.5" />
          <span>Pending Approvals</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "Pending" ? "bg-amber text-ink" : "bg-paper text-ink"
            }`}
          >
            {pendingOffers.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("Approved")}
          className={`px-4 py-2 text-xs font-mono font-semibold rounded-sm transition-all flex items-center gap-2 ${
            activeTab === "Approved"
              ? "bg-teal text-paper shadow-sm"
              : "bg-white text-ink-muted hover:text-ink hover:bg-paper case-border"
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Accepted & Dispatched</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "Approved" ? "bg-white text-teal" : "bg-paper text-ink"
            }`}
          >
            {approvedOffers.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("Rejected")}
          className={`px-4 py-2 text-xs font-mono font-semibold rounded-sm transition-all flex items-center gap-2 ${
            activeTab === "Rejected"
              ? "bg-rose text-paper shadow-sm"
              : "bg-white text-ink-muted hover:text-ink hover:bg-paper case-border"
          }`}
        >
          <XCircle className="w-3.5 h-3.5" />
          <span>Rejected Offers</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "Rejected" ? "bg-white text-rose" : "bg-paper text-ink"
            }`}
          >
            {rejectedOffers.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("All")}
          className={`px-4 py-2 text-xs font-mono font-semibold rounded-sm transition-all flex items-center gap-2 ${
            activeTab === "All"
              ? "bg-ink text-paper shadow-sm"
              : "bg-white text-ink-muted hover:text-ink hover:bg-paper case-border"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>All Offers History</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              activeTab === "All" ? "bg-paper text-ink" : "bg-paper text-ink"
            }`}
          >
            {offers.length}
          </span>
        </button>
      </div>

      {/* Main Grid: Offers List (Left 8 cols) & Live Agent Stream (Right 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Offers List */}
        <div className="lg:col-span-8 space-y-4">
          {isLoading ? (
            <div className="case-border bg-white p-12 rounded-sm text-center text-xs font-mono text-ink-muted">
              Loading offers...
            </div>
          ) : displayedOffers.length === 0 ? (
            <div className="case-border bg-white p-12 rounded-sm text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-paper text-ink-muted flex items-center justify-center mx-auto case-border">
                {activeTab === "Approved" ? (
                  <CheckCircle2 className="w-6 h-6 text-teal" />
                ) : activeTab === "Rejected" ? (
                  <XCircle className="w-6 h-6 text-rose" />
                ) : (
                  <Inbox className="w-6 h-6 text-amber" />
                )}
              </div>
              <h3 className="font-display font-bold text-lg tracking-tight text-ink">
                {activeTab === "Pending"
                  ? "All Pending Offers Reviewed!"
                  : activeTab === "Approved"
                  ? "No Approved Offers Yet"
                  : activeTab === "Rejected"
                  ? "No Rejected Offers"
                  : "No Offers Found"}
              </h3>
              <p className="text-xs text-ink-muted max-w-md mx-auto leading-relaxed">
                {activeTab === "Pending"
                  ? "There are currently no AI-drafted retention offers waiting for human review. Run a proactive batch scan or submit a support ticket to trigger new agent drafts."
                  : activeTab === "Approved"
                  ? "When you approve offers from the Pending queue, they will appear here with confirmation and dispatch details."
                  : activeTab === "Rejected"
                  ? "Offers rejected during human review are archived here for audit."
                  : "No offers matching the current view."}
              </p>
              {activeTab !== "Pending" && (
                <div className="pt-2">
                  <button
                    onClick={() => setActiveTab("Pending")}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-ink text-paper text-xs font-mono font-medium rounded-sm"
                  >
                    Go to Pending Approvals ({pendingOffers.length})
                  </button>
                </div>
              )}
            </div>
          ) : (
            displayedOffers.map((offer) => {
              const isEditing = editingOfferId === offer.id;
              const isApproved = offer.status === "Approved";
              const isRejected = offer.status === "Rejected";
              const isPending = !isApproved && !isRejected;

              return (
                <div
                  key={offer.id}
                  className={`case-border bg-white rounded-sm p-6 space-y-4 transition-all ${
                    isApproved
                      ? "border-l-4 border-l-teal"
                      : isRejected
                      ? "border-l-4 border-l-rose/80"
                      : "risk-accent-amber border-l-4 border-l-amber hover:border-ink/30"
                  }`}
                >
                  {/* Top Bar: Customer Info + Risk Badge + Status */}
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
                        {isApproved && (
                          <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-teal/15 text-teal rounded case-border border-teal/30">
                            Accepted & Dispatched
                          </span>
                        )}
                        {isRejected && (
                          <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-rose/15 text-rose rounded case-border border-rose/30">
                            Rejected
                          </span>
                        )}
                      </div>
                      <div className="text-xs font-mono text-ink-muted">
                        Baseline {offer.baseline_score ?? "—"} · Urgency {offer.urgency_score ?? "—"} · Fused {offer.fused_score ?? "—"}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-1 text-xs font-mono font-bold rounded case-border ${
                          isApproved
                            ? "bg-teal/15 text-teal"
                            : isRejected
                            ? "bg-rose/15 text-rose line-through"
                            : "bg-amber/15 text-amber"
                        }`}
                      >
                        {isApproved ? "Granted Discount: " : "Proposed Discount: "}
                        {offer.discount_percent}%
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
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-[11px] font-mono font-semibold text-ink uppercase">
                        {isApproved
                          ? "Dispatched Retention Message"
                          : isRejected
                          ? "Declined Message Draft"
                          : `Drafted Retention Offer Message ${isEditing ? "(Editing)" : ""}`}
                      </label>
                      {isApproved && (
                        <span className="text-[11px] font-mono text-teal flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Sent to Customer
                        </span>
                      )}
                    </div>

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
                      <div
                        className={`p-3.5 case-border rounded-sm text-xs leading-relaxed font-sans ${
                          isApproved
                            ? "bg-teal/5 text-ink border-teal/20"
                            : isRejected
                            ? "bg-paper/40 text-ink-muted"
                            : "bg-white text-ink"
                        }`}
                      >
                        &quot;{offer.drafted_message}&quot;
                      </div>
                    )}
                  </div>

                  {/* Footer Bar: Timestamps & Action Buttons */}
                  <div className="pt-3 case-border-t flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-ink-muted">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-ink-muted" />
                        <span>Created: {formatLiveDateTime(offer.created_at)}</span>
                        <span className="text-ink-muted/60">({formatRelativeTime(offer.created_at)})</span>
                      </span>

                      {offer.decided_at && (
                        <span className="flex items-center gap-1 font-semibold text-ink">
                          <span>
                            {isApproved ? "Approved on: " : "Rejected on: "}
                            {formatLiveDateTime(offer.decided_at)}
                          </span>
                          <span className="text-ink-muted font-normal">({formatRelativeTime(offer.decided_at)})</span>
                        </span>
                      )}
                    </div>

                    {/* Action buttons (only displayed for pending offers) */}
                    {isPending ? (
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
                    ) : isApproved ? (
                      <div className="flex items-center gap-2 text-xs font-mono text-teal font-semibold">
                        <Send className="w-3.5 h-3.5" />
                        <span>Dispatched to Customer</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-xs font-mono text-rose font-medium">
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Declined & Archived</span>
                      </div>
                    )}
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
