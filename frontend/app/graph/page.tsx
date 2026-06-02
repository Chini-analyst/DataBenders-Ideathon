"use client";

import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { NodeDetailPanel } from "@/components/graph/NodeDetailPanel";
import { GraphFilter } from "@/components/graph/GraphFilter";
import { useGraph } from "@/hooks/useGraph";
import { GitFork, RefreshCw, AlertCircle } from "lucide-react";

export default function GraphPage() {
  const {
    filteredData,
    stats,
    loading,
    error,
    selectedNode,
    neighbourhood,
    neighbourhoodLoading,
    neighbourhoodDepth,
    activeTypes,
    toggleType,
    selectAllTypes,
    deselectAllTypes,
    activeRelTypes,
    toggleRelType,
    selectAllRelTypes,
    deselectAllRelTypes,
    fetchGraph,
    selectNode,
    changeDepth,
  } = useGraph();

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gold-500/10 border border-gold-500/20">
            <GitFork className="w-6 h-6 text-gold-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">Knowledge Graph</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Click any node to explore its connections up to 3 hops away
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {stats && (
            <div className="flex gap-4 text-sm">
              <span className="text-slate-400">
                <span className="text-gold-400 font-semibold">{filteredData.nodes.length}</span>
                <span className="text-slate-600">/{stats.total_nodes}</span>
                {" "}nodes
              </span>
              <span className="text-slate-400">
                <span className="text-gold-400 font-semibold">{filteredData.edges.length}</span>
                <span className="text-slate-600">/{stats.total_edges}</span>
                {" "}edges
              </span>
            </div>
          )}
          <button
            onClick={fetchGraph}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-navy-800 border border-navy-600 text-slate-300 hover:border-gold-500/50 hover:text-gold-400 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-900/20 border border-red-800/50 text-red-400 text-sm flex-shrink-0">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Main graph area */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Filter sidebar */}
        <GraphFilter
          stats={stats}
          activeTypes={activeTypes}
          onToggleType={toggleType}
          onSelectAllTypes={selectAllTypes}
          onDeselectAllTypes={deselectAllTypes}
          activeRelTypes={activeRelTypes}
          onToggleRelType={toggleRelType}
          onSelectAllRelTypes={selectAllRelTypes}
          onDeselectAllRelTypes={deselectAllRelTypes}
        />

        {/* Graph canvas */}
        <div className="flex-1 min-w-0 relative">
          <GraphCanvas
            data={filteredData}
            loading={loading}
            selectedNode={selectedNode}
            onNodeClick={selectNode}
          />
        </div>

        {/* Node detail panel */}
        {selectedNode && (
          <NodeDetailPanel
            node={selectedNode}
            neighbourhood={neighbourhood}
            neighbourhoodLoading={neighbourhoodLoading}
            depth={neighbourhoodDepth}
            onDepthChange={changeDepth}
            onClose={() => selectNode(null)}
            onNodeClick={selectNode}
          />
        )}
      </div>
    </div>
  );
}
