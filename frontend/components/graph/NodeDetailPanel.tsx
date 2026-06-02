"use client";

import { GraphData, GraphNode } from "@/lib/api";
import { X, ArrowRight, Loader2, Network } from "lucide-react";

// All entity types from the new ingestion pipeline
const NODE_TYPE_COLORS: Record<string, string> = {
  // tabular types
  Person:            "text-blue-400 bg-blue-500/10 border-blue-500/20",
  Department:        "text-gold-400 bg-gold-500/10 border-gold-500/20",
  JobTitle:          "text-violet-400 bg-violet-500/10 border-violet-500/20",
  Skill:             "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  Project:           "text-orange-400 bg-orange-500/10 border-orange-500/20",
  Location:          "text-green-400 bg-green-500/10 border-green-500/20",
  SalaryBand:        "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  EmploymentType:    "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
  PerformanceRating: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  Status:            "text-slate-300 bg-slate-500/10 border-slate-500/20",
  Priority:          "text-red-400 bg-red-500/10 border-red-500/20",
  ProficiencyLevel:  "text-teal-400 bg-teal-500/10 border-teal-500/20",
  Certification:     "text-lime-400 bg-lime-500/10 border-lime-500/20",
  Client:            "text-pink-400 bg-pink-500/10 border-pink-500/20",
  Budget:            "text-amber-400 bg-amber-500/10 border-amber-500/20",
  Date:              "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
  Headcount:         "text-sky-400 bg-sky-500/10 border-sky-500/20",
  Category:          "text-purple-400 bg-purple-500/10 border-purple-500/20",
  EmployeeID:        "text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/20",
  Entity:            "text-slate-400 bg-slate-500/10 border-slate-500/20",
  // legacy NER types
  Organization:      "text-gold-400 bg-gold-500/10 border-gold-500/20",
  Concept:           "text-purple-400 bg-purple-500/10 border-purple-500/20",
  Document:          "text-orange-400 bg-orange-500/10 border-orange-500/20",
  Unknown:           "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

interface NodeDetailPanelProps {
  node: GraphNode;
  neighbourhood: GraphData;
  neighbourhoodLoading: boolean;
  depth: number;
  onDepthChange: (d: number) => void;
  onClose: () => void;
  onNodeClick: (node: GraphNode) => void;
}

export function NodeDetailPanel({
  node,
  neighbourhood,
  neighbourhoodLoading,
  depth,
  onDepthChange,
  onClose,
  onNodeClick,
}: NodeDetailPanelProps) {
  const typeColor = NODE_TYPE_COLORS[node.type] ?? NODE_TYPE_COLORS.Unknown;

  // Group edges by relationship type for a cleaner display
  const edgesByRel: Record<string, { edge: typeof neighbourhood.edges[0]; otherNode: GraphNode | undefined }[]> = {};
  for (const edge of neighbourhood.edges) {
    // Only show edges directly connected to the selected node
    if (edge.source !== node.id && edge.target !== node.id) continue;
    const otherNodeId = edge.source === node.id ? edge.target : edge.source;
    const otherNode = neighbourhood.nodes.find((n) => n.id === otherNodeId);
    if (!edgesByRel[edge.relationship]) edgesByRel[edge.relationship] = [];
    edgesByRel[edge.relationship].push({ edge, otherNode });
  }

  const directEdgeCount = Object.values(edgesByRel).reduce((s, arr) => s + arr.length, 0);
  const totalNodes = neighbourhood.nodes.length;
  const totalEdges = neighbourhood.edges.length;

  return (
    <div className="w-80 flex-shrink-0 bg-navy-900 border border-navy-700 rounded-xl overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-navy-700 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-slate-100 truncate text-base">{node.label}</h3>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border mt-1 ${typeColor}`}>
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

      {/* Depth selector */}
      <div className="px-4 py-2.5 border-b border-navy-700 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Network className="w-3.5 h-3.5 text-gold-400" />
          <span>Neighbourhood depth</span>
        </div>
        <div className="flex gap-1">
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => onDepthChange(d)}
              className={`w-6 h-6 rounded text-xs font-medium transition-all ${
                depth === d
                  ? "bg-gold-500/20 text-gold-400 border border-gold-500/40"
                  : "text-slate-500 hover:text-slate-300 border border-transparent"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      {!neighbourhoodLoading && (
        <div className="px-4 py-2 border-b border-navy-700 flex gap-4 text-xs text-slate-500">
          <span><span className="text-slate-300 font-medium">{totalNodes}</span> nodes</span>
          <span><span className="text-slate-300 font-medium">{totalEdges}</span> edges</span>
          <span><span className="text-slate-300 font-medium">{directEdgeCount}</span> direct connections</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Properties */}
        {Object.keys(node.properties).length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Properties
            </h4>
            <div className="space-y-1.5">
              {Object.entries(node.properties).map(([key, value]) => (
                <div key={key} className="flex flex-col gap-0.5">
                  <span className="text-xs text-slate-600 capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-sm text-slate-300 break-words">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Direct connections grouped by relationship */}
        {neighbourhoodLoading ? (
          <div className="flex items-center gap-2 text-slate-500 text-xs py-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Loading neighbourhood...
          </div>
        ) : directEdgeCount > 0 ? (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Direct connections
            </h4>
            <div className="space-y-3">
              {Object.entries(edgesByRel).map(([rel, items]) => (
                <div key={rel}>
                  <p className="text-xs font-medium text-gold-400/80 mb-1.5 flex items-center gap-1">
                    <ArrowRight className="w-3 h-3" />
                    {rel.replace(/_/g, " ")}
                    <span className="text-slate-600 font-normal">({items.length})</span>
                  </p>
                  <div className="space-y-1 pl-4">
                    {items.map(({ edge, otherNode }) => {
                      const otherColor = NODE_TYPE_COLORS[otherNode?.type ?? "Unknown"] ?? NODE_TYPE_COLORS.Unknown;
                      return (
                        <button
                          key={edge.id}
                          onClick={() => otherNode && onNodeClick(otherNode)}
                          className="w-full flex items-center gap-2 p-1.5 rounded-lg bg-navy-800/60 hover:bg-navy-800 border border-navy-700/50 hover:border-navy-600 transition-all text-left"
                        >
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs border flex-shrink-0 ${otherColor}`}>
                            {otherNode?.type ?? "?"}
                          </span>
                          <span className="text-xs text-slate-300 truncate">
                            {otherNode?.label ?? (edge.source === node.id ? edge.target : edge.source)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-600 py-2">No connections found</p>
        )}

        {/* 2nd-degree summary — nodes reachable but not directly connected */}
        {!neighbourhoodLoading && depth > 1 && totalNodes > directEdgeCount + 1 && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Extended neighbourhood ({depth}-hop)
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {neighbourhood.nodes
                .filter((n) => {
                  if (n.id === node.id) return false;
                  // Exclude nodes that are direct neighbours
                  return !Object.values(edgesByRel)
                    .flat()
                    .some(({ otherNode }) => otherNode?.id === n.id);
                })
                .slice(0, 20)
                .map((n) => {
                  const c = NODE_TYPE_COLORS[n.type] ?? NODE_TYPE_COLORS.Unknown;
                  return (
                    <button
                      key={n.id}
                      onClick={() => onNodeClick(n)}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border transition-all hover:opacity-80 ${c}`}
                    >
                      {n.label}
                    </button>
                  );
                })}
              {neighbourhood.nodes.filter((n) => {
                if (n.id === node.id) return false;
                return !Object.values(edgesByRel).flat().some(({ otherNode }) => otherNode?.id === n.id);
              }).length > 20 && (
                <span className="text-xs text-slate-600 self-center">
                  +{neighbourhood.nodes.filter((n) => {
                    if (n.id === node.id) return false;
                    return !Object.values(edgesByRel).flat().some(({ otherNode }) => otherNode?.id === n.id);
                  }).length - 20} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Source doc */}
        {node.doc_id && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
              Source document
            </h4>
            <p className="text-xs text-slate-500 font-mono break-all">{node.doc_id}</p>
          </div>
        )}
      </div>
    </div>
  );
}
