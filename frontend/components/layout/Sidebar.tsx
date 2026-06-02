"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Upload, GitFork, Bot } from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  {
    href: "/upload",
    label: "Data Upload",
    icon: Upload,
    description: "Ingest documents",
  },
  {
    href: "/graph",
    label: "Knowledge Graph",
    icon: GitFork,
    description: "Explore entities",
  },
  {
    href: "/assistant",
    label: "AI Assistant",
    icon: Bot,
    description: "Query knowledge base",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-navy-900 border-r border-navy-700 flex flex-col z-40">
      {/* Logo / Brand */}
      <div className="p-6 border-b border-navy-700">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold-500 to-gold-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-gold-900/30">
            <span className="text-navy-950 font-bold text-sm">SS</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100 leading-tight">
              StrategyShifu
            </h1>
            <p className="text-xs text-slate-500 leading-tight">
              Knowledge Graph AI
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="text-xs font-medium text-slate-600 uppercase tracking-wider px-3 mb-3">
          Navigation
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group",
                isActive
                  ? "bg-gold-500/10 border border-gold-500/20 text-gold-400"
                  : "text-slate-400 hover:bg-navy-800 hover:text-slate-200 border border-transparent"
              )}
            >
              <Icon
                className={clsx(
                  "w-4 h-4 flex-shrink-0",
                  isActive ? "text-gold-400" : "text-slate-500 group-hover:text-slate-300"
                )}
              />
              <div className="min-w-0">
                <div className="text-sm font-medium leading-tight">{item.label}</div>
                <div
                  className={clsx(
                    "text-xs leading-tight mt-0.5",
                    isActive ? "text-gold-500/70" : "text-slate-600"
                  )}
                >
                  {item.description}
                </div>
              </div>
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-gold-400 flex-shrink-0" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-navy-700">
        <p className="text-xs text-slate-600 px-1">v1.0.0 · LightRAG + Gemini</p>
      </div>
    </aside>
  );
}
