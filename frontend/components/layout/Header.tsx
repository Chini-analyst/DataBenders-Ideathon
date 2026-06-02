"use client";

import { usePathname } from "next/navigation";
import { Bell, Settings } from "lucide-react";

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "/upload": {
    title: "Data Upload",
    subtitle: "Ingest and process strategy documents",
  },
  "/graph": {
    title: "Knowledge Graph",
    subtitle: "Visualise entity relationships",
  },
  "/assistant": {
    title: "AI Assistant",
    subtitle: "Query your knowledge base",
  },
};

export function Header() {
  const pathname = usePathname();
  const page = Object.entries(PAGE_TITLES).find(([key]) =>
    pathname.startsWith(key)
  );
  const info = page?.[1] ?? { title: "StrategyShifu", subtitle: "" };

  return (
    <header className="h-16 bg-navy-900/80 backdrop-blur-sm border-b border-navy-700 flex items-center justify-between px-6 flex-shrink-0 sticky top-0 z-30">
      <div>
        <h2 className="text-sm font-semibold text-slate-200">{info.title}</h2>
        {info.subtitle && (
          <p className="text-xs text-slate-500">{info.subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Status badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-navy-800 border border-navy-600 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-gold-400 animate-pulse" />
          StrategyShifu
        </div>

        <button className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-navy-800 transition-all">
          <Bell className="w-4 h-4" />
        </button>
        <button className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-navy-800 transition-all">
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
