"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Ticket, CustomerDetail } from "../../lib/types";
import { api } from "../../lib/api";
import { formatLiveDateTime, formatRelativeTime } from "../../lib/formatters";
import {
  Ticket as TicketIcon,
  Smile,
  Meh,
  Frown,
  Plus,
  Send,
  User,
  Bot,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";

export default function TicketQueuePage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [customerDetail, setCustomerDetail] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // New ticket modal form state
  const [showNewModal, setShowNewModal] = useState(false);
  const [selectedCustId, setSelectedCustId] = useState("CUST-1000");
  const [ticketMessage, setTicketMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets();
      setTickets(data);
      if (data.length > 0 && !selectedTicket) {
        handleSelectTicket(data[0]);
      }
    } catch (err) {
      console.error("Failed to load tickets", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const handleSelectTicket = async (ticket: Ticket) => {
    setSelectedTicket(ticket);
    try {
      const cust = await api.getCustomerById(ticket.customer_id);
      setCustomerDetail(cust);
    } catch (err) {
      setCustomerDetail(null);
    }
  };

  const handleCreateTicketSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketMessage.trim()) return;

    setSubmitting(true);
    try {
      const res = await api.createTicket(selectedCustId, ticketMessage);
      setTicketMessage("");
      setShowNewModal(false);
      await fetchTickets();
      handleSelectTicket(res.ticket);
    } catch (err) {
      alert("Failed to submit ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  // Section 5: Show "Angry · Urgency 92"
  const getSentimentBadge = (label: "Angry" | "Neutral" | "Happy", urgency?: number) => {
    const u = urgency !== undefined ? urgency : 50;
    switch (label) {
      case "Angry":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-semibold bg-rose/15 text-rose rounded-sm case-border">
            <Frown className="w-3.5 h-3.5" /> Angry · Urgency {u}
          </span>
        );
      case "Happy":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-semibold bg-teal/15 text-teal rounded-sm case-border">
            <Smile className="w-3.5 h-3.5" /> Happy · Urgency {u}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono font-semibold bg-amber/15 text-amber rounded-sm case-border">
            <Meh className="w-3.5 h-3.5" /> Neutral · Urgency {u}
          </span>
        );
    }
  };

  const baselineVal = selectedTicket?.baseline_score ?? customerDetail?.churn_risk_score ?? 70;
  const urgencyVal = selectedTicket?.urgency_score ?? 50;
  const fusedVal = selectedTicket?.fused_score ?? Math.round(0.7 * baselineVal + 0.3 * urgencyVal);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 case-border-b">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
            Support Ticket Queue
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Real-time ticket sentiment scoring and AI support responses.
          </p>
        </div>

        <button
          onClick={() => setShowNewModal(true)}
          className="px-4 py-2 bg-ink text-paper text-xs font-mono font-semibold rounded-sm case-border hover:bg-ink/90 transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4 text-amber" />
          <span>Simulate Incoming Ticket</span>
        </button>
      </div>

      {/* Main Split View: Queue List (Left 40%) + Detail Thread (Right 60%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Ticket List Column */}
        <div className="lg:col-span-5 case-border bg-white rounded-sm overflow-hidden flex flex-col h-[680px]">
          <div className="p-4 bg-paper/60 case-border-b flex items-center justify-between">
            <span className="text-xs font-semibold text-ink uppercase tracking-wider font-mono">
              Inbox Queue ({tickets.length})
            </span>
            <span className="text-xs text-ink-muted font-mono">
              VADER Sentiment Analyzed
            </span>
          </div>

          <div className="divide-y divide-line overflow-y-auto flex-1">
            {loading ? (
              <div className="p-8 text-center text-xs text-ink-muted font-mono">Loading support tickets...</div>
            ) : tickets.length === 0 ? (
              <div className="p-8 text-center text-xs text-ink-muted">No tickets found in queue.</div>
            ) : (
              tickets.map((tck) => {
                const isSelected = selectedTicket?.id === tck.id;
                const urgency = tck.urgency_score ?? tck.sentiment_score;
                return (
                  <button
                    key={tck.id}
                    onClick={() => handleSelectTicket(tck)}
                    className={`w-full text-left p-4 transition-all flex flex-col gap-2 ${
                      isSelected
                        ? "bg-paper/90 border-l-4 border-l-ink"
                        : "hover:bg-paper/40"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-ink">{tck.customer_name || tck.customer_id}</span>
                      <span className="text-xs text-ink-muted font-mono">
                        {formatRelativeTime(tck.created_at)}
                      </span>
                    </div>

                    <p className="text-sm text-ink-muted/90 line-clamp-2 leading-relaxed">
                      &quot;{tck.message}&quot;
                    </p>

                    <div className="flex items-center justify-between pt-1">
                      {getSentimentBadge(tck.sentiment_label, urgency)}
                      <span className="text-xs text-ink-muted font-mono">#{tck.id}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Ticket Detail Thread Column */}
        <div className="lg:col-span-7 case-border bg-white rounded-sm p-6 flex flex-col justify-between h-[680px]">
          {selectedTicket ? (
            <div className="flex flex-col h-full justify-between">
              {/* Top Banner with Customer Risk Score */}
              <div>
                <div className="pb-4 case-border-b flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="text-xs font-mono font-medium text-ink-muted bg-paper px-2 py-0.5 rounded case-border">{selectedTicket.id}</span>
                      <h2 className="font-semibold text-xl tracking-tight text-ink">
                        {selectedTicket.customer_name || selectedTicket.customer_id}
                      </h2>
                    </div>
                    <p className="text-xs text-ink-muted mt-1 font-mono">
                      Created: {formatLiveDateTime(selectedTicket.created_at)} ({formatRelativeTime(selectedTicket.created_at)})
                    </p>
                  </div>

                  {/* Section 5: Three small stat blocks: Baseline, Urgency, Fused (emphasized) */}
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 case-border p-2 rounded bg-paper">
                      <div className="px-2 py-1 text-center">
                        <div className="text-[10px] text-ink-muted uppercase font-mono font-semibold">Baseline</div>
                        <div className="font-bold text-sm text-ink font-mono">{baselineVal}</div>
                      </div>
                      <div className="h-6 w-px bg-line" />
                      <div className="px-2 py-1 text-center">
                        <div className="text-[10px] text-ink-muted uppercase font-mono font-semibold">Urgency</div>
                        <div className="font-bold text-sm text-ink font-mono">{urgencyVal}</div>
                      </div>
                      <div className="h-6 w-px bg-line" />
                      <div className="px-2.5 py-1 text-center bg-purple-100 rounded case-border border-purple-300">
                        <div className="text-[10px] text-purple-900 uppercase font-mono font-extrabold">Fused</div>
                        <div className="font-extrabold text-base text-purple-900 font-mono">{fusedVal}</div>
                      </div>
                    </div>

                    {customerDetail && (
                      <Link
                        href={`/customers/${customerDetail.id}`}
                        className="text-xs text-ink hover:text-amber font-semibold flex items-center gap-1 transition-colors p-2 case-border rounded bg-white"
                      >
                        Profile <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>

                {/* Conversation Thread */}
                <div className="py-6 space-y-6 overflow-y-auto max-h-[460px] pr-2">
                  {/* Customer Message Bubble */}
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-paper case-border flex items-center justify-center shrink-0 text-ink">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="case-border p-4 rounded-sm bg-paper/60 space-y-2 max-w-xl">
                      <div className="flex items-center justify-between gap-4 text-xs">
                        <span className="font-semibold text-ink">
                          {selectedTicket.customer_name || "Customer"}
                        </span>
                        {getSentimentBadge(selectedTicket.sentiment_label, urgencyVal)}
                      </div>
                      <p className="text-sm text-ink leading-relaxed">
                        {selectedTicket.message}
                      </p>
                    </div>
                  </div>

                  {/* AI Support Agent Reply Bubble */}
                  {selectedTicket.agent_reply && (
                    <div className="flex items-start gap-3 flex-row-reverse">
                      <div className="w-8 h-8 rounded-full bg-ink text-paper flex items-center justify-center shrink-0">
                        <Bot className="w-4 h-4 text-amber" />
                      </div>
                      <div className="case-border p-4 rounded-sm bg-ink/5 space-y-2 max-w-xl text-left border-ink/20">
                        <div className="flex items-center justify-between text-xs pb-1">
                          <span className="font-semibold text-ink flex items-center gap-1.5 font-mono">
                            <Bot className="w-3.5 h-3.5 text-amber" /> ChurnGuardAI Support Agent (AI)
                          </span>
                          <span className="text-[11px] text-ink-muted font-mono">FAQ Retrieval</span>
                        </div>
                        <p className="text-sm text-ink leading-relaxed">
                          {selectedTicket.agent_reply}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Bar */}
              <div className="pt-4 case-border-t flex items-center justify-between text-xs font-mono">
                <span className="text-ink-muted">
                  VADER Compound: <span className="font-semibold text-ink">{selectedTicket.sentiment_score}/100</span> ({selectedTicket.sentiment_label})
                </span>

                <Link
                  href="/approvals"
                  className="px-4 py-2 bg-amber text-ink font-semibold rounded-sm hover:bg-amber/90 transition-colors flex items-center gap-1.5 shadow-sm"
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>View Pending Offers</span>
                </Link>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-ink-muted font-mono">
              Select a support ticket from the queue to view thread details.
            </div>
          )}
        </div>
      </div>

      {/* Simulate Ticket Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-ink/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white case-border rounded-sm p-6 w-full max-w-md space-y-4">
            <h3 className="font-display font-bold text-xl tracking-tight text-ink">
              Simulate Incoming Ticket
            </h3>
            <p className="text-xs text-ink-muted">
              Submitting this ticket will trigger the reactive LangGraph agent pipeline live.
            </p>

            <form onSubmit={handleCreateTicketSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono font-medium text-ink uppercase mb-1">
                  Select Customer
                </label>
                <select
                  value={selectedCustId}
                  onChange={(e) => setSelectedCustId(e.target.value)}
                  className="w-full p-2 text-xs case-border rounded bg-paper text-ink font-mono focus:outline-none"
                >
                  <option value="CUST-1000">Lucas Vance (CUST-1000 - High Risk)</option>
                  <option value="CUST-1001">Elena Rostova (CUST-1001 - High Risk)</option>
                  <option value="CUST-1002">Sophia Chen (CUST-1002 - High Risk)</option>
                  <option value="CUST-1003">Devon Miller (CUST-1003 - Watching)</option>
                  <option value="CUST-1004">Marcus Sterling (CUST-1004 - Safe)</option>
                  <option value="CUST-1005">Amara Thorne (CUST-1005 - Safe)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono font-medium text-ink uppercase mb-1">
                  Ticket Message
                </label>
                <textarea
                  rows={4}
                  value={ticketMessage}
                  onChange={(e) => setTicketMessage(e.target.value)}
                  placeholder="e.g. My order was damaged upon arrival. Very upset!"
                  className="w-full p-2.5 text-xs case-border rounded bg-paper text-ink focus:outline-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 bg-paper case-border text-ink text-xs font-mono rounded hover:bg-line transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-ink text-paper text-xs font-mono font-semibold rounded case-border hover:bg-ink/90 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5 text-amber" />
                  <span>{submitting ? "Analyzing..." : "Submit Ticket"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
