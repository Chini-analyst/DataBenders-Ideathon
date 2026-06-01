"use client";

import { GraphNode, GraphEdge } from "@/lib/api";
import { X, ArrowRight } from "lucide-react";

const NODE_TYPE_COLORS: Record<string, string> = {
  Organization: "text-gold-400 bg-gold-500/10 border-gold-500/20",
  Person: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  Concept: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  Location: "text-green-400 bg-green-500/10 border-green-500/20",
  Document: "text-orange-400 bg-orange-500/10 border-orange-500/20",
  Unknown: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

interface NodeDetailPanelProps {
  node: GraphNode;
  neighbours: { nodes: GraphNode[]; edges: GraphEdge[] };
  onClose: () => void;
}

export function NodeDetailPanel({
  node,
  neighbours,
  onClose,
}: NodeDetailPanelProps) {
  const typeColor =
    NODE_TYPE_COLORS[node.type] ?? NODE_TYPE_COLORS.Unknown;

  return (
    <div className="w-72 flex-shrink-0 bg-navy-900 border border-navy-700 rounded-xl overflow-hidden flex flex-col animate-slide-in">
      {/* Header */}
      <div className="p-4 border-b border-navy-700 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-100 truncate">{node.label}</h3>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border mt-1 ${typeColor}`}
          >
            {node.type}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-navy-800 transition-all flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Properties */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {Object.keys(node.properties).length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Properties
            </h4>
            <div className="space-y-2">
              {Object.entries(node.properties).map(([key, value]) => (
                <div key={key} className="flex flex-col gap-0.5">
                  <span className="text-xs text-slate-500 capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="text-sm text-slate-200 break-words">
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connections */}
        {neighbours.edges.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Connections ({neighbours.edges.length})
            </h4>
            <div className="space-y-2">
              {neighbours.edges.map((edge) => {
                const isSource = edge.source === node.id;
                const otherNodeId = isSource ? edge.target : edge.source;
                const otherNode = neighbours.nodes.find(
                  (n) => n.id === otherNodeId
                );
                const otherTypeColor =
                  NODE_TYPE_COLORS[otherNode?.type ?? "Unknown"] ??
                  NODE_TYPE_COLORS.Unknown;

                return (
                  <div
                    key={edge.id}
                    className="flex items-center gap-2 p-2 rounded-lg bg-navy-800 border border-navy-700"
                  >
                    {!isSource && (
                      <span className="text-xs text-slate-500 truncate max-w-[60px]">
                        {otherNode?.label ?? otherNodeId}
                      </span>
                    )}
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <ArrowRight className="w-3 h-3 text-slate-600" />
                      <span className="text-xs font-medium text-gold-400/80 bg-gold-500/5 px-1.5 py-0.5 rounded">
                        {edge.relationship}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-600" />
                    </div>
                    {isSource && (
                      <span className="text-xs text-slate-500 truncate max-w-[60px]">
                        {otherNode?.label ?? otherNodeId}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {node.doc_id && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
              Source Document
            </h4>
            <p className="text-xs text-slate-400 font-mono break-all">
              {node.doc_id}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
