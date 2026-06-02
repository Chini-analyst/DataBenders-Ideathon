"use client";

import { Source } from "@/lib/api";
import { X, FileText, GitFork, BarChart2 } from "lucide-react";
import { clsx } from "clsx";

interface SourcePanelProps {
  sources: Source[];
  onClose: () => void;
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-navy-700 overflow-hidden">
        <div
          className="h-full rounded-full bg-gold-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

export function SourcePanel({ sources, onClose }: SourcePanelProps) {
  return (
    <div className="w-80 flex-shrink-0 bg-navy-900 border border-navy-700 rounded-xl overflow-hidden flex flex-col animate-slide-in">
      {/* Header */}
      <div className="p-4 border-b border-navy-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-gold-400" />
          <h3 className="text-sm font-medium text-slate-200">
            Sources ({sources.length})
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-navy-800 transition-all"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Source list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {sources.length === 0 ? (
          <p className="text-sm text-slate-600 text-center py-8">
            No sources available
          </p>
        ) : (
          sources.map((source, idx) => (
            <div
              key={source.id}
              className="p-3 rounded-lg bg-navy-800 border border-navy-700 space-y-2"
            >
              {/* Source header */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  {source.source_type === "graph" ? (
                    <GitFork className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
                  ) : (
                    <FileText className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
                  )}
                  <span
                    className={clsx(
                      "text-xs font-medium capitalize",
                      source.source_type === "graph"
                        ? "text-purple-400"
                        : "text-blue-400"
                    )}
                  >
                    {source.source_type}
                  </span>
                </div>
                <span className="text-xs text-slate-600">#{idx + 1}</span>
              </div>

              {/* Relevance score */}
              <ScoreBar score={source.score} />

              {/* Text excerpt */}
              <p className="text-xs text-slate-400 leading-relaxed line-clamp-4">
                {source.text}
              </p>

              {/* Metadata */}
              {source.filename && (
                <p className="text-xs text-slate-600 truncate">
                  📄 {source.filename}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
