"use client";

import { useState, useCallback, useEffect } from "react";
import { api, GraphData, GraphNode, GraphEdge, GraphStats } from "@/lib/api";

export function useGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set());

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, statsData] = await Promise.all([
        api.getGraphData(),
        api.getGraphStats(),
      ]);
      setGraphData(data);
      setStats(statsData);
      // Initialise all types as active
      const types = new Set(data.nodes.map((n) => n.type));
      setActiveTypes(types);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const filteredData = useCallback((): GraphData => {
    if (activeTypes.size === 0) return graphData;
    const filteredNodes = graphData.nodes.filter((n) => activeTypes.has(n.type));
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, activeTypes]);

  const toggleType = useCallback((type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  const selectNode = useCallback((node: GraphNode | null) => {
    setSelectedNode(node);
  }, []);

  const getNodeNeighbours = useCallback(
    (nodeId: string): { nodes: GraphNode[]; edges: GraphEdge[] } => {
      const connectedEdges = graphData.edges.filter(
        (e) => e.source === nodeId || e.target === nodeId
      );
      const neighbourIds = new Set<string>();
      connectedEdges.forEach((e) => {
        neighbourIds.add(e.source);
        neighbourIds.add(e.target);
      });
      const neighbourNodes = graphData.nodes.filter((n) => neighbourIds.has(n.id));
      return { nodes: neighbourNodes, edges: connectedEdges };
    },
    [graphData]
  );

  return {
    graphData,
    filteredData: filteredData(),
    stats,
    loading,
    error,
    selectedNode,
    activeTypes,
    fetchGraph,
    toggleType,
    selectNode,
    getNodeNeighbours,
  };
}
