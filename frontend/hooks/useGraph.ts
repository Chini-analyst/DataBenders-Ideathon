"use client";

import { useState, useCallback, useEffect } from "react";
import { api, GraphData, GraphNode, GraphEdge, GraphStats } from "@/lib/api";

export function useGraph() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [neighbourhood, setNeighbourhood] = useState<GraphData>({ nodes: [], edges: [] });
  const [neighbourhoodLoading, setNeighbourhoodLoading] = useState(false);
  const [neighbourhoodDepth, setNeighbourhoodDepth] = useState(2);

  // ── Filter state ──────────────────────────────────────────────────────
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set());
  const [activeRelTypes, setActiveRelTypes] = useState<Set<string>>(new Set());

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
      setActiveTypes(new Set(data.nodes.map((n) => n.type)));
      setActiveRelTypes(new Set(data.edges.map((e) => e.relationship)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // ── Neighbourhood ─────────────────────────────────────────────────────
  const fetchNeighbourhood = useCallback(
    async (nodeId: string, depth: number) => {
      setNeighbourhoodLoading(true);
      try {
        const data = await api.getNodeNeighbourhood(nodeId, depth);
        setNeighbourhood(data);
      } catch {
        const connectedEdges = graphData.edges.filter(
          (e) => e.source === nodeId || e.target === nodeId
        );
        const ids = new Set<string>();
        connectedEdges.forEach((e) => { ids.add(e.source); ids.add(e.target); });
        setNeighbourhood({
          nodes: graphData.nodes.filter((n) => ids.has(n.id)),
          edges: connectedEdges,
        });
      } finally {
        setNeighbourhoodLoading(false);
      }
    },
    [graphData]
  );

  // ── Filtered view ─────────────────────────────────────────────────────
  const filteredData = useCallback((): GraphData => {
    // Filter nodes by active entity types
    const filteredNodes = activeTypes.size === 0
      ? []
      : graphData.nodes.filter((n) => activeTypes.has(n.type));

    const nodeIds = new Set(filteredNodes.map((n) => n.id));

    // Filter edges: both endpoints must be visible AND relationship type must be active
    const filteredEdges = graphData.edges.filter(
      (e) =>
        nodeIds.has(e.source) &&
        nodeIds.has(e.target) &&
        (activeRelTypes.size === 0 || activeRelTypes.has(e.relationship))
    );

    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, activeTypes, activeRelTypes]);

  // ── Node type toggles ─────────────────────────────────────────────────
  const toggleType = useCallback((type: string) => {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const selectAllTypes = useCallback(() => {
    setActiveTypes(new Set(graphData.nodes.map((n) => n.type)));
  }, [graphData.nodes]);

  const deselectAllTypes = useCallback(() => {
    setActiveTypes(new Set());
  }, []);

  // ── Relationship type toggles ─────────────────────────────────────────
  const toggleRelType = useCallback((rel: string) => {
    setActiveRelTypes((prev) => {
      const next = new Set(prev);
      if (next.has(rel)) next.delete(rel);
      else next.add(rel);
      return next;
    });
  }, []);

  const selectAllRelTypes = useCallback(() => {
    setActiveRelTypes(new Set(graphData.edges.map((e) => e.relationship)));
  }, [graphData.edges]);

  const deselectAllRelTypes = useCallback(() => {
    setActiveRelTypes(new Set());
  }, []);

  // ── Node selection ────────────────────────────────────────────────────
  const selectNode = useCallback(
    (node: GraphNode | null) => {
      setSelectedNode(node);
      if (node) {
        fetchNeighbourhood(node.id, neighbourhoodDepth);
      } else {
        setNeighbourhood({ nodes: [], edges: [] });
      }
    },
    [fetchNeighbourhood, neighbourhoodDepth]
  );

  const changeDepth = useCallback(
    (depth: number) => {
      setNeighbourhoodDepth(depth);
      if (selectedNode) {
        fetchNeighbourhood(selectedNode.id, depth);
      }
    },
    [selectedNode, fetchNeighbourhood]
  );

  return {
    graphData,
    filteredData: filteredData(),
    stats,
    loading,
    error,
    selectedNode,
    neighbourhood,
    neighbourhoodLoading,
    neighbourhoodDepth,
    // entity type filters
    activeTypes,
    toggleType,
    selectAllTypes,
    deselectAllTypes,
    // relationship type filters
    activeRelTypes,
    toggleRelType,
    selectAllRelTypes,
    deselectAllRelTypes,
    // actions
    fetchGraph,
    selectNode,
    changeDepth,
  };
}
