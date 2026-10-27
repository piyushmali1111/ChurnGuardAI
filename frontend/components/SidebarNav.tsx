"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Ticket,
  Inbox,
  Users,
  Settings,
  ShieldAlert,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useOffersStore } from "../lib/store";

export function SidebarNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { offers, fetchPendingOffers } = useOffersStore();

  useEffect(() => {
    fetchPendingOffers();
  }, [fetchPendingOffers]);

  const pendingCount = offers.length;

  const navItems = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/tickets", label: "Ticket Queue", icon: Ticket },
    {
      href: "/approvals",
      label: "Approval Inbox",
      icon: Inbox,
      badge: pendingCount > 0 ? pendingCount : undefined,
      highlight: true,
    },
    { href: "/customers", label: "Customers", icon: Users },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <>
      {/* Mobile Top Navbar Bar */}
      <div className="md:hidden flex items-center justify-between bg-ink text-paper px-4 py-3 border-b border-line sticky top-0 z-40">
        <div className="flex items-center gap-2 font-display font-bold text-lg tracking-tight">
          <ShieldAlert className="w-5 h-5 text-amber" />
          <span>ChurnGuardAI</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded text-paper hover:bg-white/10 transition-colors"
          aria-label="Toggle Navigation Menu"
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Overlay Backdrop for Mobile */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-ink/60 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Persistent Left Rail Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-ink text-paper flex flex-col justify-between transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="p-6 border-b border-white/15 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded bg-amber/20 border border-amber/40 flex items-center justify-center text-amber group-hover:scale-105 transition-transform">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h1 className="font-display text-xl font-extrabold tracking-tight text-paper">
                  ChurnGuardAI
                </h1>
                <p className="text-[11px] font-medium text-paper/70 uppercase tracking-wider">
                  Ops & Churn AI
                </p>
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5" aria-label="Main Navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-md text-sm font-medium transition-all ${
                    isActive
                      ? "bg-paper text-ink shadow-sm font-semibold"
                      : "text-paper/80 hover:bg-white/10 hover:text-paper"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`w-4 h-4 ${
                        isActive ? "text-ink" : "text-paper/70"
                      }`}
                    />
                    <span>{item.label}</span>
                  </div>

                  {item.badge !== undefined && (
                    <span
                      className={`px-2 py-0.5 text-xs font-mono font-bold rounded-full ${
                        isActive
                          ? "bg-amber text-ink"
                          : "bg-amber/90 text-ink"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer Info Box */}
        <div className="p-4 border-t border-white/15 m-3 rounded bg-white/5">
          <div className="flex items-center gap-2 text-xs font-medium text-paper/80 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-amber animate-pulse" />
            <span>Agent Guard Active</span>
          </div>
          <p className="text-[12px] text-paper/60 leading-tight">
            Logged in as Support Ops Manager
          </p>
        </div>
      </aside>
    </>
  );
}
