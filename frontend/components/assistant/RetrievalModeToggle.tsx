"use client";

import { RetrievalMode } from "@/hooks/useChat";
import { clsx } from "clsx";
import { Search, GitFork, Layers } from "lucide-react";

const MODES: {
  value: RetrievalMode;
  label: string;
  icon: React.ElementType;
  description: string;
}[] = [
  {
    value: "semantic",
    label: "Semantic",
    icon: Search,
    description: "Vector similarity search",
  },
  {
    value: "graph",
    label: "Graph",
    icon: GitFork,
    description: "Knowledge graph traversal",
  },
  {
    value: "hybrid",
    label: "Hybrid",
    icon: Layers,
    description: "Combined retrieval",
  },
];

interface RetrievalModeToggleProps {
  mode: RetrievalMode;
  onChange: (mode: RetrievalMode) => void;
}

export function RetrievalModeToggle({ mode, onChange }: RetrievalModeToggleProps) {
  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-navy-800 border border-navy-700">
      {MODES.map((m) => {
        const Icon = m.icon;
        const isActive = mode === m.value;
        return (
          <button
            key={m.value}
            onClick={() => onChange(m.value)}
            title={m.description}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
              isActive
                ? "bg-gold-500/10 border border-gold-500/20 text-gold-400"
                : "text-slate-500 hover:text-slate-300 border border-transparent"
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
