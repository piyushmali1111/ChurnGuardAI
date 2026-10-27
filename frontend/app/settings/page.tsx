"use client";

import { useEffect, useState } from "react";
import { SettingsConfig } from "../../lib/types";
import { api } from "../../lib/api";
import { ShieldCheck, Save, RefreshCw, CheckCircle2, Sliders } from "lucide-react";

export default function SettingsPage() {
  const [config, setConfig] = useState<SettingsConfig & { scan_frequency?: string; fusion_alpha?: number }>({
    max_discount_percent: 25,
    risk_threshold: 60,
    scan_frequency: "daily",
    fusion_alpha: 0.7,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadSettings() {
      try {
        const data = await api.getSettings();
        setConfig(data);
      } catch (err) {
        console.error("Failed to load settings:", err);
      } finally {
        setLoading(false);
      }
    }
    loadSettings();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateSettings({
        risk_threshold: Number(config.risk_threshold),
        max_discount_percent: Number(config.max_discount_percent),
        scan_frequency: config.scan_frequency || config.proactive_scan_frequency || "daily",
      });
      setConfig(updated);
      setSavedMessage("Verifier Agent rules & proactive scan configuration saved successfully!");
      setTimeout(() => setSavedMessage(null), 3500);
    } catch (err) {
      console.error("Failed to save settings:", err);
      setSavedMessage("Failed to save settings. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const currentFrequency = config.scan_frequency || config.proactive_scan_frequency || "daily";

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="pb-4 case-border-b">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
          Agent Rules & System Settings
        </h1>
        <p className="text-sm text-ink-muted mt-1">
          Configure business guardrails enforced by the Verifier Agent and schedule proactive churn scans.
        </p>
      </div>

      {savedMessage && (
        <div className="p-3 case-border bg-teal/10 border-teal/40 text-teal text-xs font-mono rounded flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{savedMessage}</span>
        </div>
      )}

      {/* Settings Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Verifier Agent Guardrails */}
        <div className="case-border bg-white rounded-sm p-6 space-y-6">
          <div className="flex items-center gap-2 pb-3 case-border-b">
            <ShieldCheck className="w-5 h-5 text-amber" />
            <div>
              <h2 className="font-display font-bold text-lg tracking-tight text-ink">
                Verifier Agent Guardrails
              </h2>
              <p className="text-xs text-ink-muted">
                Rule-based safety ceiling preventing agents from issuing overly generous discounts.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-mono font-semibold text-ink uppercase mb-2">
                Maximum Discount Percentage Allowed (%)
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={5}
                  max={50}
                  disabled={loading}
                  value={config.max_discount_percent}
                  onChange={(e) =>
                    setConfig({ ...config, max_discount_percent: Number(e.target.value) })
                  }
                  className="w-full p-2.5 text-sm font-mono case-border rounded bg-paper text-ink focus:outline-none"
                />
              </div>
              <p className="text-[11px] text-ink-muted mt-1">
                If the Retention Agent drafts an offer exceeding this limit, the Verifier Agent automatically rejects it.
              </p>
            </div>

            <div>
              <label className="block text-xs font-mono font-semibold text-ink uppercase mb-2">
                Churn Risk Trigger Threshold (0–100)
              </label>
              <input
                type="number"
                min={10}
                max={95}
                disabled={loading}
                value={config.risk_threshold}
                onChange={(e) =>
                  setConfig({ ...config, risk_threshold: Number(e.target.value) })
                }
                className="w-full p-2.5 text-sm font-mono case-border rounded bg-paper text-ink focus:outline-none"
              />
              <p className="text-[11px] text-ink-muted mt-1">
                Customers with a combined risk score at or above this value will be flagged for an offer draft.
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: Core Formula Parameters (Read-Only) */}
        <div className="case-border bg-white rounded-sm p-6 space-y-4">
          <div className="flex items-center gap-2 pb-3 case-border-b">
            <Sliders className="w-5 h-5 text-ink" />
            <div>
              <h2 className="font-display font-bold text-lg tracking-tight text-ink">
                Risk Fusion Parameters
              </h2>
              <p className="text-xs text-ink-muted">
                Core formula weights from the research paper defining multimodal fusion.
              </p>
            </div>
          </div>

          <div className="p-3 bg-paper case-border rounded text-xs font-mono text-ink">
            <span className="font-bold">Fusion weight (alpha): {config.fusion_alpha ?? 0.7}</span>
            <span className="text-ink-muted ml-2">— behavioral risk 70%, live urgency 30%</span>
          </div>
        </div>

        {/* Section 3: Proactive Scan Schedule */}
        <div className="case-border bg-white rounded-sm p-6 space-y-6">
          <div className="flex items-center gap-2 pb-3 case-border-b">
            <RefreshCw className="w-5 h-5 text-ink" />
            <div>
              <h2 className="font-display font-bold text-lg tracking-tight text-ink">
                APScheduler Proactive Scan Frequency
              </h2>
              <p className="text-xs text-ink-muted">
                Schedule batch scoring jobs for silent churners who haven&apos;t filed support tickets.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-semibold text-ink uppercase mb-2">
              Automated Scan Cadence
            </label>
            <div className="flex items-center gap-6 text-xs font-mono">
              <label className="flex items-center gap-2 cursor-pointer p-3 case-border rounded bg-paper w-full max-w-xs">
                <input
                  type="radio"
                  name="frequency"
                  value="daily"
                  checked={currentFrequency === "daily"}
                  onChange={() => setConfig({ ...config, scan_frequency: "daily" })}
                />
                <span className="font-bold text-ink">Daily Cron Job (Recommended)</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer p-3 case-border rounded bg-paper w-full max-w-xs">
                <input
                  type="radio"
                  name="frequency"
                  value="weekly"
                  checked={currentFrequency === "weekly"}
                  onChange={() => setConfig({ ...config, scan_frequency: "weekly" })}
                />
                <span className="font-bold text-ink">Weekly Sunday Scan</span>
              </label>
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end">
          <button
            type="submit"
            disabled={saving || loading}
            className="px-6 py-2.5 bg-ink text-paper font-mono font-bold text-xs rounded-sm case-border hover:bg-ink/90 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4 text-amber" />
            <span>{saving ? "Saving..." : "Save Configuration Rules"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
