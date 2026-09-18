import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import type { TraceResultResponse, TraceHopItem, VASPAttributionResponse } from '../types/api';
import { ZoomIn, ZoomOut, RefreshCw, Maximize2, ExternalLink, Clock, Hash, Layers, Filter } from 'lucide-react';
import { buildExplorerUrl } from '../utils/explorer';
import { formatCurrency, formatTimeInterval, formatExactNumber } from '../utils/formatters';

interface FundFlowGraphProps {
  traceData?: TraceResultResponse;
  vaspData?: VASPAttributionResponse;
  selectedPathId?: string;
  onSelectPath?: (pathId: string) => void;
  onNodeClick: (address: string, role: string) => void;
  onEdgeClick: (hop: TraceHopItem) => void;
}

export interface NodePosition {
  id: string;
  address: string;
  role: 'STARTING' | 'INTERMEDIARY' | 'KNOWN_ENTITY' | 'VASP_ENDPOINT' | 'TRACE_ENDPOINT';
  x: number;
  y: number;
  hopLevel: number;
  label: string;
  vaspName?: string;
}

export interface EdgePosition {
  id: string;
  from: string;
  to: string;
  amount: number;
  hop: TraceHopItem;
  pathIds: string[];
}

export const FundFlowGraph: React.FC<FundFlowGraphProps> = ({
  traceData,
  vaspData,
  selectedPathId,
  onSelectPath,
  onNodeClick,
  onEdgeClick,
}) => {
  // View mode: 'TOP' (top 3 paths) or 'ALL' (all paths)
  const [viewMode, setViewMode] = useState<'TOP' | 'ALL'>('TOP');

  // Interactive viewport transform (pan & zoom)
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Hover state for interactive tooltips
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Determine top 3 paths vs all paths
  const { pathsToDisplay, totalPathsCount } = useMemo(() => {
    if (!traceData?.paths || traceData.paths.length === 0) {
      return { pathsToDisplay: [], totalPathsCount: 0 };
    }
    const allPaths = traceData.paths;
    const sortedPaths = [...allPaths].sort(
      (a, b) => (b.relevance_score || 0) - (a.relevance_score || 0)
    );
    const top3 = sortedPaths.slice(0, 3);
    return {
      pathsToDisplay: viewMode === 'TOP' ? top3 : sortedPaths,
      totalPathsCount: allPaths.length,
    };
  }, [traceData, viewMode]);

  // VASP Candidate Endpoints Set
  const vaspAddresses = useMemo(() => {
    const set = new Set<string>();
    if (vaspData?.candidates) {
      vaspData.candidates.forEach((c) => set.add(c.endpoint_address));
    }
    return set;
  }, [vaspData]);

  // HIERARCHICAL / DAG HOP-BASED LAYOUT CALCULATION
  const { nodes, edges, graphBounds } = useMemo(() => {
    if (!traceData || pathsToDisplay.length === 0) {
      return { nodes: [], edges: [], graphBounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 } };
    }

    const startWallet = traceData.starting_wallet;
    const nodeHopMap = new Map<string, number>();
    const nodeRoleMap = new Map<string, NodePosition['role']>();
    const edgeMap = new Map<string, EdgePosition>();

    // 1. Identify all nodes with outgoing transfers (part of continuing fund-flow paths)
    const outgoingAddresses = new Set<string>();
    pathsToDisplay.forEach((path) => {
      path.hops.forEach((h) => {
        outgoingAddresses.add(h.from_address);
      });
    });

    // 2. Calculate minimum hop level & collect edges
    pathsToDisplay.forEach((path) => {
      const seq = path.wallet_sequence || [];
      seq.forEach((addr, idx) => {
        // Minimum hop level across paths
        const currentHop = nodeHopMap.get(addr);
        if (currentHop === undefined || idx < currentHop) {
          nodeHopMap.set(addr, idx);
        }
      });

      // Collect Edges
      path.hops.forEach((h) => {
        const edgeId = `${h.from_address}->${h.to_address}`;
        const normalizedHop: TraceHopItem = {
          ...h,
          explorer_url: buildExplorerUrl(h.tx_hash, h.asset, h.explorer_url),
        };

        if (edgeMap.has(edgeId)) {
          const existing = edgeMap.get(edgeId)!;
          if (!existing.pathIds.includes(path.path_id)) {
            existing.pathIds.push(path.path_id);
          }
        } else {
          edgeMap.set(edgeId, {
            id: edgeId,
            from: h.from_address,
            to: h.to_address,
            amount: h.amount,
            hop: normalizedHop,
            pathIds: [path.path_id],
          });
        }
      });
    });

    // 3. Assign semantic node roles accurately
    nodeHopMap.forEach((_, addr) => {
      let role: NodePosition['role'] = 'INTERMEDIARY';
      if (addr === startWallet) {
        role = 'STARTING';
      } else if (vaspAddresses.has(addr)) {
        role = 'VASP_ENDPOINT';
      } else if (addr.startsWith('TB')) {
        role = 'KNOWN_ENTITY';
      } else if (!outgoingAddresses.has(addr)) {
        // Tracing currently ends at this wallet because no further relevant downstream transfer was discovered
        role = 'TRACE_ENDPOINT';
      } else {
        role = 'INTERMEDIARY';
      }
      nodeRoleMap.set(addr, role);
    });

    // 2. Group nodes into hop columns
    const columnsMap = new Map<number, string[]>();
    nodeHopMap.forEach((hopLevel, addr) => {
      if (!columnsMap.has(hopLevel)) columnsMap.set(hopLevel, []);
      columnsMap.get(hopLevel)!.push(addr);
    });

    // Sorted hop levels: 0, 1, 2, ...
    const hopLevels = Array.from(columnsMap.keys()).sort((a, b) => a - b);

    // 3. Coordinate calculation constants
    const COLUMN_SPACING = 270; // Horizontal distance between hops (px)
    const NODE_VERTICAL_SPACING = 115; // Vertical distance between sibling nodes (px)

    const nodePosMap = new Map<string, { x: number; y: number; hopLevel: number }>();

    // Position Column 0 (Starting Wallet)
    if (columnsMap.has(0)) {
      const col0Nodes = columnsMap.get(0)!;
      col0Nodes.forEach((addr, i) => {
        nodePosMap.set(addr, {
          x: 0,
          y: (i - (col0Nodes.length - 1) / 2) * NODE_VERTICAL_SPACING,
          hopLevel: 0,
        });
      });
    }

    // Position subsequent Columns (1..N) with parent-guided vertical ordering to minimize line crossings
    hopLevels.forEach((hopLevel) => {
      if (hopLevel === 0) return;
      const colNodes = columnsMap.get(hopLevel)!;

      // Calculate average parent Y coordinate for each node in this column
      const nodeParentY = new Map<string, number>();
      colNodes.forEach((addr) => {
        let parentYSum = 0;
        let parentCount = 0;
        edgeMap.forEach((e) => {
          if (e.to === addr && nodePosMap.has(e.from)) {
            parentYSum += nodePosMap.get(e.from)!.y;
            parentCount++;
          }
        });
        nodeParentY.set(addr, parentCount > 0 ? parentYSum / parentCount : 0);
      });

      // Sort nodes in column by parent Y coordinate to keep related branches visually grouped
      colNodes.sort((a, b) => (nodeParentY.get(a) || 0) - (nodeParentY.get(b) || 0));

      // Compute Y positions centered around median
      const totalColHeight = (colNodes.length - 1) * NODE_VERTICAL_SPACING;
      const startY = -totalColHeight / 2;

      colNodes.forEach((addr, idx) => {
        const x = hopLevel * COLUMN_SPACING;
        const y = startY + idx * NODE_VERTICAL_SPACING;
        nodePosMap.set(addr, { x, y, hopLevel });
      });
    });

    // Build Node objects
    const formattedNodes: NodePosition[] = Array.from(nodePosMap.entries()).map(([addr, pos]) => {
      const role = nodeRoleMap.get(addr) || 'INTERMEDIARY';
      let vaspName: string | undefined;

      if (role === 'VASP_ENDPOINT' && vaspData?.candidates) {
        const matched = vaspData.candidates.find((c) => c.endpoint_address === addr);
        if (matched) vaspName = matched.candidate_name;
      }

      return {
        id: addr,
        address: addr,
        role,
        x: pos.x,
        y: pos.y,
        hopLevel: pos.hopLevel,
        label: truncateAddress(addr),
        vaspName,
      };
    });

    const formattedEdges = Array.from(edgeMap.values());

    // Calculate Graph Bounding Box
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;

    if (formattedNodes.length > 0) {
      formattedNodes.forEach((n) => {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      });
    } else {
      minX = 0;
      maxX = 0;
      minY = 0;
      maxY = 0;
    }

    // Node padding offset for bounds calculation
    minX -= 70;
    maxX += 90;
    minY -= 70;
    maxY += 90;

    return {
      nodes: formattedNodes,
      edges: formattedEdges,
      graphBounds: { minX, maxX, minY, maxY },
    };
  }, [traceData, pathsToDisplay, vaspAddresses, vaspData]);

  // Active path fallback selection
  const activePathId = selectedPathId || traceData?.paths?.[0]?.path_id || '';

  // Helper: Address truncation
  function truncateAddress(addr: string) {
    if (!addr || addr.length < 10) return addr;
    return `${addr.substring(0, 4)}...${addr.substring(addr.length - 4)}`;
  }

  // AUTO-FIT VIEWPORT ENGINE: Fit graph nicely to viewport container
  const fitGraph = useCallback(() => {
    if (!containerRef.current || nodes.length === 0) return;

    const containerWidth = containerRef.current.clientWidth || 900;
    const containerHeight = containerRef.current.clientHeight || 580;

    const boundsWidth = graphBounds.maxX - graphBounds.minX || 300;
    const boundsHeight = graphBounds.maxY - graphBounds.minY || 300;

    const paddingX = 80;
    const paddingY = 60;

    const scaleX = (containerWidth - 2 * paddingX) / boundsWidth;
    const scaleY = (containerHeight - 2 * paddingY) / boundsHeight;

    // Clamp scale for optimal legibility (never microscopically small, never huge)
    let calculatedScale = Math.min(scaleX, scaleY);
    calculatedScale = Math.max(0.4, Math.min(1.15, calculatedScale));

    const graphCenterX = (graphBounds.minX + graphBounds.maxX) / 2;
    const graphCenterY = (graphBounds.minY + graphBounds.maxY) / 2;

    const targetX = containerWidth / 2 - graphCenterX * calculatedScale;
    const targetY = containerHeight / 2 - graphCenterY * calculatedScale;

    setTransform({
      x: targetX,
      y: targetY,
      scale: calculatedScale,
    });
  }, [graphBounds, nodes.length]);

  // Auto-fit on layout calculation or view mode toggle
  useEffect(() => {
    // Delay slightly to ensure DOM container measurement is accurate
    const timer = setTimeout(() => {
      fitGraph();
    }, 40);
    return () => clearTimeout(timer);
  }, [fitGraph, viewMode, traceData?.trace_id]);

  // Pan & Drag Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    // Only drag on left click and on SVG background
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setTransform((prev) => ({
        ...prev,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      }));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Zoom Handlers
  const handleZoomIn = () => {
    setTransform((prev) => ({
      ...prev,
      scale: Math.min(1.8, prev.scale * 1.15),
    }));
  };

  const handleZoomOut = () => {
    setTransform((prev) => ({
      ...prev,
      scale: Math.max(0.3, prev.scale / 1.15),
    }));
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    setTransform((prev) => ({
      ...prev,
      scale: Math.max(0.3, Math.min(1.8, prev.scale * zoomFactor)),
    }));
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden mb-8 font-sans">
      {/* Canvas Top Bar */}
      <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-[#3730A3]" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-700 font-sans">
              Fund Flow Graph (Hierarchical DAG Layout)
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 font-sans">
            Left-to-right hop progression showing starting wallet, intermediaries, trace endpoints, and VASP endpoints.
          </p>
        </div>

        {/* Path View Mode Filter Toggle */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center bg-slate-100 p-0.5 rounded border border-slate-200 font-sans text-xs">
            <button
              onClick={() => setViewMode('TOP')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                viewMode === 'TOP'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
              title="Show top 3 relevant investigation paths"
            >
              <span className="flex items-center space-x-1">
                <Filter className="w-3 h-3 text-[#3730A3]" />
                <span>TOP PATHS ({Math.min(3, totalPathsCount)})</span>
              </span>
            </button>

            <button
              onClick={() => setViewMode('ALL')}
              className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                viewMode === 'ALL'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
              title="Show all paths discovered in this trace"
            >
              <span>ALL PATHS ({totalPathsCount})</span>
            </button>
          </div>

          {/* Zoom & Viewport Controls */}
          <div className="flex items-center space-x-1 bg-white p-1 rounded border border-slate-200 text-slate-600 shadow-xs">
            <button
              onClick={fitGraph}
              className="p-1 hover:bg-slate-100 rounded text-[#3730A3] font-medium"
              title="Fit Graph to Viewport"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomIn}
              className="p-1 hover:bg-slate-100 rounded"
              title="Zoom In (+)"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono px-1.5 tabular-nums font-semibold text-slate-700">
              {Math.round(transform.scale * 100)}%
            </span>
            <button
              onClick={handleZoomOut}
              className="p-1 hover:bg-slate-100 rounded"
              title="Zoom Out (-)"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={fitGraph}
              className="p-1 hover:bg-slate-100 rounded ml-0.5 text-slate-500"
              title="Reset View"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Graph Legend Sub-header */}
      <div className="px-6 py-2 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between text-[11px] font-sans">
        <div className="flex items-center space-x-5 flex-wrap gap-y-1">
          <div className="flex items-center space-x-1.5 text-indigo-900 font-semibold">
            <span className="w-3 h-3 rounded-full bg-indigo-600 inline-block border border-white shadow-2xs" />
            <span>STARTING WALLET</span>
          </div>

          <div className="flex items-center space-x-1.5 text-slate-700">
            <span className="w-3 h-3 rounded-full bg-white border-2 border-slate-500 inline-block" />
            <span>INTERMEDIARY</span>
          </div>

          <div className="flex items-center space-x-1.5 text-teal-800 font-medium">
            <span className="w-3 h-3 bg-teal-600 rounded-2xs inline-block" />
            <span>KNOWN ENTITY</span>
          </div>

          <div className="flex items-center space-x-1.5 text-amber-900 font-semibold">
            <span className="w-3 h-3 bg-amber-100 border border-dashed border-amber-600 rounded-2xs inline-block" />
            <span>TRACE ENDPOINT</span>
          </div>

          <div className="flex items-center space-x-1.5 text-indigo-950 font-bold">
            <span className="w-3 h-3 bg-indigo-900 rotate-45 rounded-2xs inline-block" />
            <span>VASP ENDPOINT</span>
          </div>
        </div>

        <div className="text-[10px] text-slate-500 font-sans italic">
          Hop sequence flows left → right • Drag to pan • Scroll to zoom
        </div>
      </div>

      {/* SVG Canvas Area or Empty State */}
      {nodes.length === 0 ? (
        <div className="relative min-h-[580px] h-[620px] w-full graph-canvas-bg overflow-hidden flex flex-col items-center justify-center text-center p-6">
          <div className="bg-white border border-slate-200 p-8 rounded-xl shadow-sm max-w-md space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800 font-mono">
              NO GRAPH PATHS AVAILABLE
            </h3>
            <p className="text-xs text-slate-500 font-sans leading-relaxed">
              Initiate an investigation with active multi-hop transactions to trace real fund movements visually.
            </p>
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="relative min-h-[580px] h-[620px] w-full graph-canvas-bg overflow-hidden select-none"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <svg
            ref={svgRef}
            className={`w-full h-full ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
          >
            <defs>
              {/* Active / Selected Arrow Marker */}
              <marker
                id="arrow-active"
                viewBox="0 0 10 10"
                refX="16"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#4338ca" />
              </marker>

              {/* Inactive / Dimmed Arrow Marker */}
              <marker
                id="arrow-inactive"
                viewBox="0 0 10 10"
                refX="16"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
              </marker>
            </defs>

            {/* Viewport Transform Container */}
            <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
              {/* RENDER EDGES */}
              {edges.map((e) => {
                const fromNode = nodes.find((n) => n.id === e.from);
                const toNode = nodes.find((n) => n.id === e.to);
                if (!fromNode || !toNode) return null;

                // Path selection state
                const isSelectedPath = activePathId
                  ? e.pathIds.includes(activePathId)
                  : true;
                const isHovered = hoveredEdgeId === e.id;

                // Edge opacity (Requirement 9: non-selected paths at ~30% opacity)
                const opacity = isSelectedPath ? 1.0 : 0.3;
                const strokeWidth = isSelectedPath ? 3 : 2;

                // Bezier curve control points
                const dx = toNode.x - fromNode.x;
                const cx1 = fromNode.x + dx * 0.45;
                const cy1 = fromNode.y;
                const cx2 = fromNode.x + dx * 0.55;
                const cy2 = toNode.y;
                const pathData = `M ${fromNode.x} ${fromNode.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${toNode.x} ${toNode.y}`;

                const midX = (fromNode.x + toNode.x) / 2;
                const midY = (fromNode.y + toNode.y) / 2;

                return (
                  <g
                    key={e.id}
                    onClick={(evt) => {
                      evt.stopPropagation();
                      if (onSelectPath && e.pathIds.length > 0) {
                        onSelectPath(e.pathIds[0]);
                      }
                      onEdgeClick(e.hop);
                    }}
                    onMouseEnter={(evt) => {
                      setHoveredEdgeId(e.id);
                      setTooltipPos({ x: evt.clientX, y: evt.clientY });
                    }}
                    onMouseMove={(evt) => {
                      setTooltipPos({ x: evt.clientX, y: evt.clientY });
                    }}
                    onMouseLeave={() => {
                      setHoveredEdgeId(null);
                      setTooltipPos(null);
                    }}
                    className="cursor-pointer group"
                    style={{ opacity, transition: 'opacity 0.2s ease-in-out' }}
                  >
                    {/* Transparent thick stroke for easy mouse hover targeting */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={strokeWidth + 14}
                    />

                    {/* Smooth Curved Edge Line */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke={isSelectedPath ? (isHovered ? '#312e81' : '#4338ca') : '#94a3b8'}
                      strokeWidth={isHovered ? strokeWidth + 1 : strokeWidth}
                      strokeDasharray={isSelectedPath ? 'none' : '4,4'}
                      markerEnd={isSelectedPath ? 'url(#arrow-active)' : 'url(#arrow-inactive)'}
                    />

                    {/* EDGE AMOUNT LABEL - Default: ONLY ON HOVER OR SELECTED PATH (Requirement 11) */}
                    {(isSelectedPath || isHovered) && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x="-36"
                          y="-10"
                          width="72"
                          height="20"
                          rx="4"
                          fill="#ffffff"
                          stroke={isSelectedPath ? '#6366f1' : '#cbd5e1'}
                          strokeWidth="1.5"
                          className="shadow-2xs"
                        />
                        <text
                          y="3"
                          textAnchor="middle"
                          className="font-mono text-[10px] font-bold fill-slate-800 tabular-nums pointer-events-none"
                        >
                          {formatCurrency(e.amount)}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* RENDER NODES */}
              {nodes.map((n) => {
                const isSelectedPathNode = activePathId
                  ? pathsToDisplay
                      .find((p) => p.path_id === activePathId)
                      ?.wallet_sequence?.includes(n.address) ?? true
                  : true;

                const isHovered = hoveredNodeId === n.id;
                const opacity = isSelectedPathNode ? 1.0 : 0.3;

                return (
                  <g
                    key={n.id}
                    transform={`translate(${n.x}, ${n.y})`}
                    onClick={(evt) => {
                      evt.stopPropagation();
                      onNodeClick(n.address, n.role);
                    }}
                    onMouseEnter={() => setHoveredNodeId(n.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className="cursor-pointer"
                    style={{ opacity, transition: 'opacity 0.2s ease-in-out' }}
                  >
                    {/* Node Hover Outline */}
                    {isHovered && (
                      <circle
                        r="28"
                        fill="none"
                        stroke="#818cf8"
                        strokeWidth="2"
                        strokeDasharray="3,3"
                        className="animate-spin-slow"
                      />
                    )}

                    {/* Role Geometry Rendering */}
                    {n.role === 'STARTING' && (
                      <g>
                        <circle r="20" fill="#4338ca" stroke="#ffffff" strokeWidth="3" className="shadow-md" />
                        <circle r="6" fill="#ffffff" />
                      </g>
                    )}

                    {n.role === 'INTERMEDIARY' && (
                      <circle r="16" fill="#ffffff" stroke="#475569" strokeWidth="3" className="shadow-2xs" />
                    )}

                    {n.role === 'KNOWN_ENTITY' && (
                      <rect
                        x="-17"
                        y="-17"
                        width="34"
                        height="34"
                        rx="5"
                        fill="#0d9488"
                        stroke="#ffffff"
                        strokeWidth="2.5"
                        className="shadow-sm"
                      />
                    )}

                    {n.role === 'TRACE_ENDPOINT' && (
                      <g>
                        <rect
                          x="-16"
                          y="-16"
                          width="32"
                          height="32"
                          rx="6"
                          fill="#fffbe6"
                          stroke="#d97706"
                          strokeWidth="2.5"
                          strokeDasharray="4,2"
                          className="shadow-sm"
                        />
                        <circle r="4" fill="#d97706" />
                      </g>
                    )}

                    {n.role === 'VASP_ENDPOINT' && (
                      <g transform="rotate(45)">
                        <rect
                          x="-17"
                          y="-17"
                          width="34"
                          height="34"
                          rx="4"
                          fill="#312e81"
                          stroke="#ffffff"
                          strokeWidth="2.5"
                          className="shadow-md"
                        />
                      </g>
                    )}

                    {/* Compact Truncated Address Label (Requirement 12) */}
                    <text
                      y="34"
                      textAnchor="middle"
                      className="font-mono text-[11px] font-bold fill-slate-900 tracking-tight"
                    >
                      {n.label}
                    </text>

                    {/* Role Pill Beneath */}
                    <g transform="translate(0, 40)">
                      <rect
                        x="-48"
                        y="0"
                        width="96"
                        height="16"
                        rx="3"
                        fill={
                          n.role === 'VASP_ENDPOINT'
                            ? '#e0e7ff'
                            : n.role === 'TRACE_ENDPOINT'
                            ? '#fef3c7'
                            : n.role === 'KNOWN_ENTITY'
                            ? '#ccfbf1'
                            : n.role === 'STARTING'
                            ? '#e0e7ff'
                            : '#f1f5f9'
                        }
                        stroke={
                          n.role === 'VASP_ENDPOINT'
                            ? '#818cf8'
                            : n.role === 'TRACE_ENDPOINT'
                            ? '#f59e0b'
                            : n.role === 'KNOWN_ENTITY'
                            ? '#2dd4bf'
                            : n.role === 'STARTING'
                            ? '#818cf8'
                            : '#cbd5e1'
                        }
                        strokeWidth="1"
                      />
                      <text
                        y="11"
                        textAnchor="middle"
                        className={`font-sans text-[9px] font-bold uppercase tracking-wider ${
                          n.role === 'VASP_ENDPOINT'
                            ? 'fill-indigo-900'
                            : n.role === 'TRACE_ENDPOINT'
                            ? 'fill-amber-900'
                            : n.role === 'KNOWN_ENTITY'
                            ? 'fill-teal-900'
                            : n.role === 'STARTING'
                            ? 'fill-indigo-900'
                            : 'fill-slate-700'
                        }`}
                      >
                        {n.vaspName
                          ? n.vaspName.substring(0, 13)
                          : n.role === 'TRACE_ENDPOINT'
                          ? 'TRACE ENDPOINT'
                          : n.role === 'STARTING'
                          ? 'STARTING WALLET'
                          : n.role === 'KNOWN_ENTITY'
                          ? 'KNOWN ENTITY'
                          : n.role}
                      </text>
                    </g>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Interactive Edge Hover Tooltip (Requirement 11 Detail) */}
          {hoveredEdgeId && tooltipPos && (() => {
            const edge = edges.find((e) => e.id === hoveredEdgeId);
            if (!edge) return null;
            return (
              <div
                className="fixed z-50 pointer-events-none bg-slate-900 text-white p-3 rounded-lg shadow-xl text-xs space-y-1.5 border border-slate-700 font-sans max-w-xs"
                style={{
                  left: tooltipPos.x + 15,
                  top: tooltipPos.y - 15,
                }}
              >
                <div className="flex items-center justify-between border-b border-slate-700 pb-1.5">
                  <span className="font-mono font-bold text-indigo-300 text-xs" title={`${formatExactNumber(edge.amount)} ${edge.hop.asset || 'USDT'}`}>
                    {formatCurrency(edge.amount)} ({edge.hop.asset || 'USDT'})
                  </span>
                  <span className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                    HOP #{edge.hop.hop_number}
                  </span>
                </div>

                <div className="space-y-1 font-mono text-[11px] text-slate-300">
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3 h-3 text-slate-400 flex-shrink-0" />
                    <span>{edge.hop.timestamp ? new Date(edge.hop.timestamp).toUTCString() : 'N/A'}</span>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <span className="text-slate-400 font-bold">TRANSFER GAP:</span>
                    <span>{formatTimeInterval(edge.hop.delta_t_seconds)}</span>
                  </div>

                  <div className="flex items-center space-x-1.5 truncate">
                    <Hash className="w-3 h-3 text-slate-400 flex-shrink-0" />
                    <span className="truncate">{truncateAddress(edge.hop.tx_hash)}</span>
                  </div>
                </div>

                <div className="pt-1 text-[10px] text-indigo-400 flex items-center space-x-1">
                  <span>Click edge for full transaction evidence</span>
                  <ExternalLink className="w-3 h-3 inline" />
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Canvas Footer Hint Bar */}
      <div className="px-6 py-2.5 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between text-xs text-slate-500 font-sans gap-2">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
          <span>Click any graph node or edge to inspect verifiable evidence in drawer.</span>
        </div>
        <div className="font-mono text-slate-400 text-[11px] flex items-center space-x-3">
          <span>FIT AUTO-COMPUTED</span>
          <span>•</span>
          <span>SPATIAL STABILITY: ACTIVE</span>
        </div>
      </div>
    </div>
  );
};

