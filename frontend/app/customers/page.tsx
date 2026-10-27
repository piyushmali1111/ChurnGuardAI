"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { CustomerSummary } from "../../lib/types";
import { api } from "../../lib/api";
import { formatCurrency } from "../../lib/formatters";
import { Users, ArrowUpDown, ArrowRight, Search, ChevronLeft, ChevronRight } from "lucide-react";

export default function CustomersDirectoryPage() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [loading, setLoading] = useState(true);
  const [sortDirection, setSortDirection] = useState<"desc" | "asc">("desc");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [threshold, setThreshold] = useState<number>(60);

  // Load settings for dynamic threshold
  useEffect(() => {
    async function loadSettings() {
      try {
        const s = await api.getSettings();
        if (s?.risk_threshold) {
          setThreshold(s.risk_threshold);
        }
      } catch (err) {
        console.error("Failed to load settings:", err);
      }
    }
    loadSettings();
  }, []);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const sortKey = sortDirection === "desc" ? "risk_desc" : "risk_asc";
      const res = await api.getCustomers({
        page,
        pageSize,
        search: searchQuery.trim(),
        riskLevel: filterStatus,
        sort: sortKey,
      });
      setCustomers(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to fetch customers:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchQuery, filterStatus, sortDirection]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleToggleSort = () => {
    setSortDirection((prev) => (prev === "desc" ? "asc" : "desc"));
    setPage(1);
  };

  const handleSearchChange = (val: string) => {
    setSearchQuery(val);
    setPage(1);
  };

  const handleFilterChange = (val: string) => {
    setFilterStatus(val);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const startRecord = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endRecord = Math.min(page * pageSize, total);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 case-border-b">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">
            Customer Risk Directory
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Complete database of customers scored by XGBoost churn predictor. Scores above {threshold} auto-trigger offer drafts.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-ink-muted bg-white p-2 case-border rounded font-medium">
          <Users className="w-4 h-4 text-ink" />
          <span>
            Showing {startRecord}–{endRecord} of {total.toLocaleString()} records
          </span>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="case-border bg-white p-4 rounded-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-ink-muted absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by customer name, email, or ID..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs case-border rounded bg-paper text-ink focus:outline-none focus:ring-1 focus:ring-ink"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filterStatus}
            onChange={(e) => handleFilterChange(e.target.value)}
            className="p-2 text-xs font-mono case-border rounded bg-paper text-ink focus:outline-none"
          >
            <option value="All">All Risk Levels</option>
            <option value="High Risk">High Risk (&gt;= {threshold})</option>
            <option value="Watching">Watching ({Math.max(0, threshold - 20)} - {threshold - 1})</option>
            <option value="Safe">Safe (&lt; {Math.max(0, threshold - 20)})</option>
          </select>

          <button
            onClick={handleToggleSort}
            className="px-3 py-2 bg-paper case-border text-xs font-mono text-ink font-semibold rounded hover:bg-line transition-colors flex items-center gap-1.5"
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-amber" />
            <span>Sort Risk: {sortDirection.toUpperCase()}</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div className="case-border bg-white rounded-sm overflow-hidden shadow-none">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-paper case-border-b font-mono text-ink-muted uppercase text-[11px]">
              <tr>
                <th className="p-3.5 pl-4">Customer Name & ID</th>
                <th className="p-3.5">
                  <button onClick={handleToggleSort} className="flex items-center gap-1 hover:text-ink">
                    Churn Risk Score <ArrowUpDown className="w-3 h-3 text-amber" />
                  </button>
                </th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Last Order Date</th>
                <th className="p-3.5">Lifetime Spent</th>
                <th className="p-3.5 pr-4 text-right">Action</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-line">
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs font-mono text-ink-muted">
                    Loading customer directory...
                  </td>
                </tr>
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs text-ink-muted">
                    No matching customer records found.
                  </td>
                </tr>
              ) : (
                customers.map((cust) => (
                  <tr
                    key={cust.id}
                    className="hover:bg-paper/40 transition-colors group cursor-pointer"
                  >
                    <td className="p-3.5 pl-4">
                      <div>
                        <Link
                          href={`/customers/${cust.id}`}
                          className="font-semibold text-ink hover:underline text-sm block"
                        >
                          {cust.name}
                        </Link>
                        <span className="font-mono text-[11px] text-ink-muted">
                          {cust.id} • {cust.email}
                        </span>
                      </div>
                    </td>

                    <td className="p-3.5 font-mono">
                      <span className="text-base font-bold text-ink">
                        {cust.churn_risk_score}
                      </span>
                      <span className="text-[10px] text-ink-muted">/100</span>
                      {cust.fused_score !== undefined && cust.fused_score !== cust.churn_risk_score && (
                        <span className="ml-2 px-1.5 py-0.5 text-[10px] rounded bg-purple-100 text-purple-800 font-semibold">
                          Fused: {cust.fused_score}
                        </span>
                      )}
                    </td>

                    <td className="p-3.5">
                      <span
                        className={`px-2.5 py-0.5 text-xs font-semibold rounded ${
                          cust.churn_status === "High Risk"
                            ? "bg-rose/15 text-rose"
                            : cust.churn_status === "Watching"
                            ? "bg-amber/15 text-amber"
                            : "bg-teal/15 text-teal"
                        }`}
                      >
                        {cust.churn_status}
                      </span>
                    </td>

                    <td className="p-3.5 font-mono text-ink-muted">{cust.last_order_date}</td>

                    <td className="p-3.5 font-mono font-semibold text-ink">
                      {formatCurrency(cust.total_spent)}
                    </td>

                    <td className="p-3.5 pr-4 text-right">
                      <Link
                        href={`/customers/${cust.id}`}
                        className="inline-flex items-center gap-1 font-mono text-xs font-medium text-ink hover:text-amber group-hover:translate-x-0.5 transition-transform"
                      >
                        Case File <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server-Side Pagination Footer */}
        <div className="p-4 case-border-t bg-paper flex items-center justify-between text-xs font-mono">
          <span className="text-ink-muted">
            Page <span className="font-bold text-ink">{page}</span> of{" "}
            <span className="font-bold text-ink">{totalPages}</span> ({total.toLocaleString()} total customers)
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="px-3 py-1.5 case-border rounded bg-white text-ink hover:bg-line transition-colors flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="px-3 py-1.5 case-border rounded bg-white text-ink hover:bg-line transition-colors flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
