"use client";

import { useAgentActivityStore } from "../lib/store";
import { useAgentActivityStream } from "../lib/hooks/useAgentActivityStream";
import { Bot, CheckCircle2, AlertTriangle, Info, Tag } from "lucide-react";

export function AgentActivityWidget() {
  // Activate stream hook
  useAgentActivityStream();
  const activities = useAgentActivityStore((state) => state.activities);

  return (
    <div className="case-border bg-white rounded-sm p-4 flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 case-border-b">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-ink" />
          <h3 className="font-display font-bold text-base tracking-tight text-ink">
            Live Agent Activity
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-mono text-teal bg-teal/10 px-2 py-0.5 rounded">
          <span className="w-2 h-2 rounded-full bg-teal animate-ping" />
          <span>Stream Active</span>
        </div>
      </div>

      <div className="space-y-3 overflow-y-auto max-h-[380px] pr-1 scrollbar-thin">
        {activities.length === 0 ? (
          <div className="py-8 text-center text-xs text-ink-muted font-mono">
            Listening for multi-agent events...
          </div>
        ) : (
          activities.map((item, idx) => (
            <div
              key={item.id}
              className={`p-3 rounded-sm text-xs case-border transition-all duration-300 ease-in-out ${
                idx === 0 ? "bg-amber/5 border-amber/30 scale-[1.01]" : "bg-paper/40"
              }`}
            >
              <div className="flex items-center justify-between font-mono text-[11px] mb-1.5 gap-2">
                <span className="font-semibold text-ink flex items-center gap-1.5 truncate">
                  {item.type === "alert" && <AlertTriangle className="w-3.5 h-3.5 text-rose shrink-0" />}
                  {item.type === "success" && <CheckCircle2 className="w-3.5 h-3.5 text-teal shrink-0" />}
                  {(!item.type || item.type === "info") && <Info className="w-3.5 h-3.5 text-amber shrink-0" />}
                  <span className="truncate">{item.agent}</span>
                </span>

                <div className="flex items-center gap-1.5 shrink-0">
                  {item.chip && (
                    <span className="px-1.5 py-0.2 text-[10px] font-mono font-bold bg-ink/10 text-ink rounded case-border">
                      {item.chip}
                    </span>
                  )}
                  <span className="text-ink-muted text-[10px]">{item.timestamp}</span>
                </div>
              </div>
              <p className="text-ink-muted leading-relaxed font-sans">{item.message}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
