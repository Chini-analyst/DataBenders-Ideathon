"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { GraphData, GraphNode } from "@/lib/api";
import { Loader2, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

// Node type colour mapping
const NODE_COLORS: Record<string, string> = {
  Organization: "#f59e0b",  // gold
  Person: "#60a5fa",        // blue
  Concept: "#a78bfa",       // purple
  Location: "#34d399",      // green
  Document: "#fb923c",      // orange
  Unknown: "#94a3b8",       // slate
};

const NODE_SIZES: Record<string, number> = {
  Organization: 10,
  Person: 8,
  Concept: 7,
  Location: 8,
  Document: 9,
  Unknown: 6,
};

interface GraphCanvasProps {
  data: GraphData;
  loading: boolean;
  selectedNode: GraphNode | null;
  onNodeClick: (node: GraphNode | null) => void;
}

export function GraphCanvas({
  data,
  loading,
  selectedNode,
  onNodeClick,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [ForceGraph, setForceGraph] = useState<any>(null);
  const [mounted, setMounted] = useState(false);

  // Dynamically import react-force-graph-2d (client-only)
  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default);
      setMounted(true);
    });
  }, []);

  // Transform data for force-graph
  const graphDataForForce = {
    nodes: data.nodes.map((n) => ({
      ...n,
      id: n.id,
      name: n.label,
      color: NODE_COLORS[n.type] ?? NODE_COLORS.Unknown,
      val: NODE_SIZES[n.type] ?? 6,
    })),
    links: data.edges.map((e) => ({
      ...e,
      source: e.source,
      target: e.target,
      label: e.relationship,
    })),
  };

  const handleNodeClick = useCallback(
    (node: any) => {
      const graphNode = data.nodes.find((n) => n.id === node.id);
      onNodeClick(graphNode ?? null);
    },
    [data.nodes, onNodeClick]
  );

  const handleBackgroundClick = useCallback(() => {
    onNodeClick(null);
  }, [onNodeClick]);

  const handleZoomIn = () => {
    graphRef.current?.zoom(1.5, 400);
  };

  const handleZoomOut = () => {
    graphRef.current?.zoom(0.67, 400);
  };

  const handleFit = () => {
    graphRef.current?.zoomToFit(400, 40);
  };

  if (loading) {
    return (
      <div className="w-full h-full rounded-xl bg-navy-900 border border-navy-700 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin text-gold-400" />
          <p className="text-sm">Loading knowledge graph...</p>
        </div>
      </div>
    );
  }

  if (data.nodes.length === 0) {
    return (
      <div className="w-full h-full rounded-xl bg-navy-900 border border-dashed border-navy-700 flex items-center justify-center">
        <div className="text-center text-slate-600">
          <p className="text-sm font-medium">No graph data available</p>
          <p className="text-xs mt-1">Upload documents to populate the graph</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full rounded-xl bg-navy-900 border border-navy-700 overflow-hidden graph-canvas"
    >
      {/* Zoom controls */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded-md bg-navy-800/90 border border-navy-600 text-slate-400 hover:text-gold-400 hover:border-gold-500/50 transition-all"
          title="Zoom in"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded-md bg-navy-800/90 border border-navy-600 text-slate-400 hover:text-gold-400 hover:border-gold-500/50 transition-all"
          title="Zoom out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleFit}
          className="p-1.5 rounded-md bg-navy-800/90 border border-navy-600 text-slate-400 hover:text-gold-400 hover:border-gold-500/50 transition-all"
          title="Fit to screen"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Node count badge */}
      <div className="absolute bottom-3 left-3 z-10 flex gap-2">
        <span className="px-2 py-1 text-xs rounded-md bg-navy-800/90 border border-navy-600 text-slate-400">
          {data.nodes.length} nodes · {data.edges.length} edges
        </span>
      </div>

      {mounted && ForceGraph && containerRef.current && (
        <ForceGraph
          ref={graphRef}
          graphData={graphDataForForce}
          width={containerRef.current.clientWidth}
          height={containerRef.current.clientHeight}
          backgroundColor="#050d1a"
          nodeLabel={(node: any) => `${node.name} (${node.type})`}
          nodeColor={(node: any) =>
            selectedNode?.id === node.id ? "#fbbf24" : node.color
          }
          nodeVal={(node: any) =>
            selectedNode?.id === node.id ? node.val * 1.8 : node.val
          }
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const label = node.name;
            const fontSize = Math.max(10 / globalScale, 3);
            const r = (selectedNode?.id === node.id ? node.val * 1.8 : node.val) * 0.8;
            const color = selectedNode?.id === node.id ? "#fbbf24" : node.color;

            // Draw glow for selected
            if (selectedNode?.id === node.id) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI);
              ctx.fillStyle = `${color}33`;
              ctx.fill();
            }

            // Draw node circle
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();

            // Draw label
            if (globalScale > 0.6) {
              ctx.font = `${fontSize}px Inter, sans-serif`;
              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle = "#f1f5f9";
              ctx.fillText(label, node.x, node.y + r + fontSize + 1);
            }
          }}
          linkColor={() => "#1e3a6e"}
          linkWidth={1.5}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={() => "#2a4f8f"}
          linkLabel={(link: any) => link.label}
          linkCanvasObjectMode={() => "after"}
          linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            if (globalScale < 0.8) return;
            const start = link.source;
            const end = link.target;
            if (!start || !end || typeof start !== "object") return;

            const midX = (start.x + end.x) / 2;
            const midY = (start.y + end.y) / 2;
            const fontSize = Math.max(8 / globalScale, 2);

            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "#94a3b8";
            ctx.fillText(link.label, midX, midY);
          }}
          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      )}
    </div>
  );
}
