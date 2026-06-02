"use client";

import { GraphStats } from "@/lib/api";
import { Filter } from "lucide-react";
import { clsx } from "clsx";

const NODE_TYPE_STYLES: Record<string, { dot: string; text: string; bg: string }> = {
  Organization: { dot: "bg-gold-400", text: "text-gold-400", bg: "bg-gold-500/10 border-gold-500/20" },
  Person: { dot: "bg-blue-400", text: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
  Concept: { dot: "bg-purple-400", text: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
  Location: { dot: "bg-green-400", text: "text-green-400", bg: "bg-green-500/10 border-green-500/20" },
  Document: { dot: "bg-orange-400", text: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20" },
};

interface GraphFilterProps {
  stats: GraphStats | null;
  activeTypes: Set<string>;
  onToggleType: (type: string) => void;
}

export function GraphFilter({ stats, activeTypes, onToggleType }: GraphFilterProps) {
  if (!stats) return null;

  const nodeTypes = Object.entries(stats.node_types).sort((a, b) => b[1] - a[1]);
  const relTypes = Object.entries(stats.relationship_types).sort((a, b) => b[1] - a[1]);

  return (
    <div className="w-52 flex-shrink-0 bg-navy-900 border border-navy-700 rounded-xl p-4 flex flex-col gap-4 overflow-y-auto">
      <div className="flex items-center gap-2">
        <Filter className="w-3.5 h-3.5 text-gold-400" />
        <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          Filters
        </h3>
      </div>

      {/* Entity types */}
      <div>
        <p className="text-xs text-slate-600 mb-2">Entity Types</p>
        <div className="space-y-1.5">
          {nodeTypes.map(([type, count]) => {
            const style = NODE_TYPE_STYLES[type] ?? {
              dot: "bg-slate-400",
              text: "text-slate-400",
              bg: "bg-slate-500/10 border-slate-500/20",
            };
            const isActive = activeTypes.has(type);

            return (
              <button
                key={type}
                onClick={() => onToggleType(type)}
                className={clsx(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-xs transition-all",
                  isActive
                    ? `${style.bg} ${style.text}`
                    : "bg-transparent border-transparent text-slate-600 hover:text-slate-400"
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full flex-shrink-0",
                      isActive ? style.dot : "bg-slate-700"
                    )}
                  />
                  <span>{type}</span>
                </div>
                <span
                  className={clsx(
                    "font-medium",
                    isActive ? "" : "text-slate-700"
                  )}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Relationship types */}
      {relTypes.length > 0 && (
        <div>
          <p className="text-xs text-slate-600 mb-2">Relationships</p>
          <div className="space-y-1">
            {relTypes.map(([rel, count]) => (
              <div
                key={rel}
                className="flex items-center justify-between px-2 py-1 text-xs text-slate-500"
              >
                <span className="truncate">{rel}</span>
                <span className="text-slate-700 ml-2 flex-shrink-0">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
