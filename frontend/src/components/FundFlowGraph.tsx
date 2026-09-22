import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import type {
  TraceResultResponse,
  TraceHopItem,
  VASPAttributionResponse,
  GraphNodeRole,
  GraphNodeDetail,
  VASPAttributionCandidate,
} from '../types/api';
import {
  ZoomIn,
  ZoomOut,
  RefreshCw,
  Maximize2,
  ExternalLink,
  Clock,
  Hash,
  Layers,
  Filter,
  Compass,
  FileCode,
  ShieldCheck,
} from 'lucide-react';
import { buildExplorerUrl } from '../utils/explorer';
import { formatCurrency, formatTimeInterval, formatExactNumber } from '../utils/formatters';

interface FundFlowGraphProps {
  traceData?: TraceResultResponse | null;
  vaspData?: VASPAttributionResponse | null;
  selectedPathId?: string;
  onSelectPath?: (pathId: string) => void;
  onNodeClick: (address: string, role: GraphNodeRole, detail: GraphNodeDetail) => void;
  onEdgeClick: (hop: TraceHopItem) => void;
}

export interface NodePosition {
  id: string;
  address: string;
  role: GraphNodeRole;
  x: number;
  y: number;
  hopLevel: number;
  label: string;
  entityLabel?: string;
  entityRole?: string;
  walletStatus: string;
  vaspCandidate?: VASPAttributionCandidate;
}

export interface EdgePosition {
  id: string;
  from: string;
  to: string;
  amount: number;
  hop: TraceHopItem;
  pathIds: string[];
}

const KNOWN_CONTRACT_ADDRESSES = new Set([
  'TR7NHQJEKQXGTCI8Q8ZY4PL8OTSZGJLJ6T', // Tether USD Contract
  'TEZFAYL8TEWPCEE9KWSCBRUE65GMMDTBQL', // Tether Treasury
]);

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

  // VASP Candidate Map (Address -> Candidate)
  const vaspCandidatesMap = useMemo(() => {
    const map = new Map<string, VASPAttributionCandidate>();
    if (vaspData?.candidates) {
      vaspData.candidates.forEach((c) => {
        if (c.endpoint_address) {
          map.set(c.endpoint_address.toUpperCase(), c);
        }
      });
    }
    return map;
  }, [vaspData]);

  // Helper: Address truncation
  function truncateAddress(addr: string) {
    if (!addr || addr.length < 10) return addr;
    return `${addr.substring(0, 4)}...${addr.substring(addr.length - 4)}`;
  }

  // Active path fallback selection
  const activePathId = selectedPathId || pathsToDisplay[0]?.path_id || '';

  // Identify top VASP path for the "Follow Path to VASP" quick action
  const topVaspCandidate = vaspData?.candidates?.[0];
  const pathToVasp = useMemo(() => {
    if (!topVaspCandidate?.endpoint_address || !traceData?.paths) return null;
    const target = topVaspCandidate.endpoint_address.toUpperCase();
    return traceData.paths.find((p) =>
      p.wallet_sequence?.some((w) => w.toUpperCase() === target)
    );
  }, [topVaspCandidate, traceData]);

  // HIERARCHICAL / DAG HOP-BASED LAYOUT CALCULATION
  const { nodes, edges, graphBounds, hopLevels } = useMemo(() => {
    if (!traceData || pathsToDisplay.length === 0) {
      return {
        nodes: [],
        edges: [],
        graphBounds: { minX: 0, maxX: 0, minY: 0, maxY: 0 },
        hopLevels: [],
      };
    }

    const startWallet = traceData.starting_wallet;
    const nodeHopMap = new Map<string, number>();
    const nodeRoleMap = new Map<string, GraphNodeRole>();
    const nodeDetailMap = new Map<string, Partial<NodePosition>>();
    const edgeMap = new Map<string, EdgePosition>();

    // 1. Identify all nodes with outgoing transfers
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

    // 3. Assign semantic node roles with strict classification
    nodeHopMap.forEach((_, addr) => {
      const addrUpper = addr.toUpperCase();
      let role: GraphNodeRole = 'INTERMEDIATE';
      let entityLabel: string | undefined;
      let entityRole: string | undefined;
      let walletStatus = 'Intermediate Wallet';
      let vaspCandidate: VASPAttributionCandidate | undefined;

      // RULE A: Token Contracts are NEVER treated as VASPs
      if (KNOWN_CONTRACT_ADDRESSES.has(addrUpper)) {
        role = 'TOKEN_CONTRACT';
        entityLabel = 'USDT Contract';
        entityRole = 'TOKEN_CONTRACT';
        walletStatus = 'Token Contract / Infrastructure';
      }
      // RULE B: Starting Wallet
      else if (addr === startWallet) {
        role = 'STARTING';
        walletStatus = 'Starting Wallet';
      }
      // RULE C: Verified VASP Endpoints
      else if (vaspCandidatesMap.has(addrUpper)) {
        const cand = vaspCandidatesMap.get(addrUpper)!;
        if (cand.attribution_type === 'TOKEN_CONTRACT' || cand.entity_role === 'TOKEN_CONTRACT') {
          role = 'TOKEN_CONTRACT';
          entityLabel = cand.candidate_name;
          entityRole = 'TOKEN_CONTRACT';
          walletStatus = 'Token Contract / Infrastructure';
        } else if (cand.entity_role === 'TOKEN_ISSUER' || cand.entity_role === 'BRIDGE') {
          role = 'NON_VASP_ENTITY';
          entityLabel = cand.candidate_name;
          entityRole = cand.entity_role;
          walletStatus = 'Non-VASP Entity';
        } else {
          role = 'VASP_ENDPOINT';
          entityLabel = cand.candidate_name;
          entityRole = cand.entity_role || 'EXCHANGE_HOT_WALLET';
          walletStatus = 'Verified VASP Endpoint';
          vaspCandidate = cand;
        }
      }
      // RULE D: Known Non-VASP Entity
      else if (addr.startsWith('TB') && !outgoingAddresses.has(addr)) {
        role = 'NON_VASP_ENTITY';
        entityLabel = 'Known Infrastructure';
        walletStatus = 'Non-VASP Entity';
      }
      // RULE E: Intermediate Wallets
      else if (outgoingAddresses.has(addr)) {
        role = 'INTERMEDIATE';
        walletStatus = 'Intermediate Wallet';
      }
      // RULE F: Unknown Wallet / Leaf
      else {
        role = 'UNKNOWN_WALLET';
        walletStatus = 'Unknown Wallet';
      }

      nodeRoleMap.set(addr, role);
      nodeDetailMap.set(addr, {
        role,
        entityLabel,
        entityRole,
        walletStatus,
        vaspCandidate,
      });
    });

    // 4. Group nodes into hop columns
    const columnsMap = new Map<number, string[]>();
    nodeHopMap.forEach((hopLevel, addr) => {
      if (!columnsMap.has(hopLevel)) columnsMap.set(hopLevel, []);
      columnsMap.get(hopLevel)!.push(addr);
    });

    const sortedHopLevels = Array.from(columnsMap.keys()).sort((a, b) => a - b);

    // 5. Coordinate calculation constants
    const COLUMN_SPACING = 280; // Horizontal distance between hops (px)
    const NODE_VERTICAL_SPACING = 125; // Vertical distance between sibling nodes (px)

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

    // Position subsequent Columns (1..N) with parent-guided vertical ordering
    sortedHopLevels.forEach((hopLevel) => {
      if (hopLevel === 0) return;
      const colNodes = columnsMap.get(hopLevel)!;

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

      colNodes.sort((a, b) => (nodeParentY.get(a) || 0) - (nodeParentY.get(b) || 0));

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
      const details = nodeDetailMap.get(addr) || {};
      const role = (details.role || 'INTERMEDIATE') as GraphNodeRole;

      return {
        id: addr,
        address: addr,
        role,
        x: pos.x,
        y: pos.y,
        hopLevel: pos.hopLevel,
        label: truncateAddress(addr),
        entityLabel: details.entityLabel,
        entityRole: details.entityRole,
        walletStatus: details.walletStatus || 'Wallet',
        vaspCandidate: details.vaspCandidate,
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

    minX -= 90;
    maxX += 100;
    minY -= 100;
    maxY += 110;

    return {
      nodes: formattedNodes,
      edges: formattedEdges,
      graphBounds: { minX, maxX, minY, maxY },
      hopLevels: sortedHopLevels,
    };
  }, [traceData, pathsToDisplay, vaspCandidatesMap]);

  // AUTO-FIT VIEWPORT ENGINE
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

  useEffect(() => {
    const timer = setTimeout(() => {
      fitGraph();
    }, 40);
    return () => clearTimeout(timer);
  }, [fitGraph, viewMode, traceData?.trace_id]);

  // Pan & Drag Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
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

  // Handler for Follow Path to VASP
  const handleFollowPathToVasp = () => {
    if (!pathToVasp) return;
    if (onSelectPath) {
      onSelectPath(pathToVasp.path_id);
    }
    if (topVaspCandidate) {
      const vaspNode = nodes.find((n) => n.address.toUpperCase() === topVaspCandidate.endpoint_address.toUpperCase());
      if (vaspNode) {
        onNodeClick(vaspNode.address, vaspNode.role, {
          address: vaspNode.address,
          role: vaspNode.role,
          label: vaspNode.label,
          hopLevel: vaspNode.hopLevel,
          entityLabel: vaspNode.entityLabel,
          entityRole: vaspNode.entityRole,
          walletStatus: vaspNode.walletStatus,
          isTerminal: true,
          vaspCandidate: topVaspCandidate,
        });
      }
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden mb-6 font-sans">
      {/* Canvas Top Bar */}
      <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-700" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
              FUND FLOW GRAPH — DIRECTED FORENSIC DAG
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5 font-sans">
            Central investigation workspace: Hop progression flows from Starting Wallet through Intermediaries to Verified VASP Endpoints.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3 flex-wrap gap-2">
          {/* Follow Path to VASP Button */}
          {pathToVasp && topVaspCandidate && (
            <button
              onClick={handleFollowPathToVasp}
              className="flex items-center space-x-1.5 px-3 py-1 bg-indigo-700 hover:bg-indigo-800 text-white rounded text-xs font-semibold shadow-xs transition-colors"
              title={`Highlight direct fund path from starting wallet to ${topVaspCandidate.candidate_name}`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Follow Path to {topVaspCandidate.candidate_name}</span>
            </button>
          )}

          {/* Path View Mode Filter Toggle */}
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
                <Filter className="w-3 h-3 text-indigo-700" />
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
              className="p-1 hover:bg-slate-100 rounded text-indigo-700 font-medium"
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
              title="Recenter View"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Graph Legend Sub-header (Categories distinguished) */}
      <div className="px-6 py-2 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between text-[11px] font-sans">
        <div className="flex items-center space-x-5 flex-wrap gap-y-1">
          <div className="flex items-center space-x-1.5 text-indigo-900 font-semibold">
            <span className="w-3 h-3 rounded-full bg-indigo-700 inline-block border-2 border-white shadow-2xs" />
            <span>STARTING WALLET</span>
          </div>

          <div className="flex items-center space-x-1.5 text-slate-700">
            <span className="w-3 h-3 rounded-full bg-white border-2 border-slate-500 inline-block" />
            <span>INTERMEDIATE WALLET</span>
          </div>

          <div className="flex items-center space-x-1.5 text-indigo-950 font-bold">
            <span className="w-3 h-3 bg-indigo-900 rotate-45 rounded-2xs inline-block border border-indigo-400" />
            <span>VERIFIED VASP ENDPOINT</span>
          </div>

          <div className="flex items-center space-x-1.5 text-teal-800 font-medium">
            <span className="w-3 h-3 bg-teal-600 rounded-2xs inline-block" />
            <span>NON-VASP ENTITY</span>
          </div>

          <div className="flex items-center space-x-1.5 text-slate-700 font-medium">
            <span className="w-3 h-3 bg-slate-500 rounded-2xs inline-block border border-slate-400" />
            <span>TOKEN CONTRACT (NOT A VASP)</span>
          </div>

          <div className="flex items-center space-x-1.5 text-amber-800 font-medium">
            <span className="w-3 h-3 bg-amber-100 border border-dashed border-amber-600 rounded-2xs inline-block" />
            <span>UNKNOWN WALLET</span>
          </div>
        </div>

        <div className="text-[10px] text-slate-500 font-sans italic">
          Hop progression left → right • Drag to pan • Scroll to zoom
        </div>
      </div>

      {/* SVG Canvas Area or Empty State */}
      {nodes.length === 0 ? (
        <div className="relative min-h-[500px] h-[540px] w-full graph-canvas-bg overflow-hidden flex flex-col items-center justify-center text-center p-6">
          <div className="bg-white border border-slate-200 p-8 rounded-xl shadow-xs max-w-md space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
              NO TRACE GRAPH LOADED
            </h3>
            <p className="text-xs text-slate-500 font-sans leading-relaxed">
              Enter a target wallet address and run an investigation to trace real multi-hop fund movements on TRON.
            </p>
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="relative min-h-[520px] h-[560px] w-full graph-canvas-bg overflow-hidden select-none"
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
              {/* HOP COLUMN LABELS */}
              {hopLevels.map((hop) => {
                const x = hop * 280;
                return (
                  <g key={`hop-col-${hop}`} transform={`translate(${x}, ${graphBounds.minY + 25})`}>
                    <rect
                      x="-55"
                      y="-12"
                      width="110"
                      height="20"
                      rx="4"
                      fill="#f8fafc"
                      stroke="#cbd5e1"
                      strokeWidth="1"
                    />
                    <text
                      y="2"
                      textAnchor="middle"
                      className="font-mono text-[9px] font-bold fill-slate-600 tracking-wider"
                    >
                      {hop === 0 ? 'HOP 0 (START)' : `HOP #${hop}`}
                    </text>
                  </g>
                );
              })}

              {/* RENDER EDGES */}
              {edges.map((e) => {
                const fromNode = nodes.find((n) => n.id === e.from);
                const toNode = nodes.find((n) => n.id === e.to);
                if (!fromNode || !toNode) return null;

                const isSelectedPath = activePathId ? e.pathIds.includes(activePathId) : true;
                const isHovered = hoveredEdgeId === e.id;

                const opacity = isSelectedPath ? 1.0 : 0.2;
                const strokeWidth = isSelectedPath ? 3 : 2;

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
                    {/* Transparent hover hit target */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={strokeWidth + 14}
                    />

                    {/* Curved Edge Line */}
                    <path
                      d={pathData}
                      fill="none"
                      stroke={isSelectedPath ? (isHovered ? '#312e81' : '#4338ca') : '#94a3b8'}
                      strokeWidth={isHovered ? strokeWidth + 1 : strokeWidth}
                      strokeDasharray={isSelectedPath ? 'none' : '4,4'}
                      markerEnd={isSelectedPath ? 'url(#arrow-active)' : 'url(#arrow-inactive)'}
                    />

                    {/* Edge Amount Pill */}
                    {(isSelectedPath || isHovered) && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x="-40"
                          y="-10"
                          width="80"
                          height="20"
                          rx="4"
                          fill="#ffffff"
                          stroke={isSelectedPath ? '#6366f1' : '#cbd5e1'}
                          strokeWidth="1.5"
                          className="shadow-2xs"
                        />
                        <text
                          y="3.5"
                          textAnchor="middle"
                          className="font-mono text-[10px] font-bold fill-slate-900 tabular-nums pointer-events-none"
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
                const opacity = isSelectedPathNode ? 1.0 : 0.25;

                return (
                  <g
                    key={n.id}
                    transform={`translate(${n.x}, ${n.y})`}
                    onClick={(evt) => {
                      evt.stopPropagation();
                      onNodeClick(n.address, n.role, {
                        address: n.address,
                        role: n.role,
                        label: n.label,
                        hopLevel: n.hopLevel,
                        entityLabel: n.entityLabel,
                        entityRole: n.entityRole,
                        walletStatus: n.walletStatus,
                        isTerminal: n.role === 'VASP_ENDPOINT' || n.role === 'UNKNOWN_WALLET',
                        vaspCandidate: n.vaspCandidate,
                      });
                    }}
                    onMouseEnter={() => setHoveredNodeId(n.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className="cursor-pointer"
                    style={{ opacity, transition: 'opacity 0.2s ease-in-out' }}
                  >
                    {/* Hover Glow Ring */}
                    {isHovered && (
                      <circle
                        r="30"
                        fill="none"
                        stroke="#818cf8"
                        strokeWidth="2"
                        strokeDasharray="4,3"
                      />
                    )}

                    {/* STARTING WALLET */}
                    {n.role === 'STARTING' && (
                      <g>
                        <circle r="20" fill="#4338ca" stroke="#ffffff" strokeWidth="3" className="shadow-md" />
                        <circle r="6" fill="#ffffff" />
                      </g>
                    )}

                    {/* INTERMEDIATE WALLET */}
                    {n.role === 'INTERMEDIATE' && (
                      <circle r="17" fill="#ffffff" stroke="#475569" strokeWidth="3" className="shadow-2xs" />
                    )}

                    {/* VERIFIED VASP ENDPOINT */}
                    {n.role === 'VASP_ENDPOINT' && (
                      <g>
                        <circle r="26" fill="none" stroke="#818cf8" strokeWidth="2" opacity="0.7" />
                        <g transform="rotate(45)">
                          <rect
                            x="-18"
                            y="-18"
                            width="36"
                            height="36"
                            rx="5"
                            fill="#312e81"
                            stroke="#ffffff"
                            strokeWidth="2.5"
                            className="shadow-md"
                          />
                        </g>
                        <ShieldCheck className="w-5 h-5 text-white absolute -top-2.5 -left-2.5" />
                      </g>
                    )}

                    {/* NON-VASP ENTITY */}
                    {n.role === 'NON_VASP_ENTITY' && (
                      <rect
                        x="-17"
                        y="-17"
                        width="34"
                        height="34"
                        rx="6"
                        fill="#0d9488"
                        stroke="#ffffff"
                        strokeWidth="2.5"
                        className="shadow-sm"
                      />
                    )}

                    {/* TOKEN CONTRACT */}
                    {n.role === 'TOKEN_CONTRACT' && (
                      <g>
                        <rect
                          x="-18"
                          y="-18"
                          width="36"
                          height="36"
                          rx="4"
                          fill="#475569"
                          stroke="#cbd5e1"
                          strokeWidth="2"
                          strokeDasharray="3,2"
                          className="shadow-sm"
                        />
                        <FileCode className="w-4 h-4 text-slate-200 -top-2 -left-2" />
                      </g>
                    )}

                    {/* UNKNOWN WALLET */}
                    {n.role === 'UNKNOWN_WALLET' && (
                      <g>
                        <circle
                          r="16"
                          fill="#fffbe6"
                          stroke="#d97706"
                          strokeWidth="2"
                          strokeDasharray="4,2"
                        />
                        <circle r="4" fill="#d97706" />
                      </g>
                    )}

                    {/* Truncated Address Label */}
                    <text
                      y="34"
                      textAnchor="middle"
                      className="font-mono text-[11px] font-bold fill-slate-900 tracking-tight"
                    >
                      {n.label}
                    </text>

                    {/* Role Status Pill */}
                    <g transform="translate(0, 42)">
                      <rect
                        x="-52"
                        y="0"
                        width="104"
                        height="16"
                        rx="3"
                        fill={
                          n.role === 'VASP_ENDPOINT'
                            ? '#e0e7ff'
                            : n.role === 'TOKEN_CONTRACT'
                            ? '#f1f5f9'
                            : n.role === 'NON_VASP_ENTITY'
                            ? '#ccfbf1'
                            : n.role === 'STARTING'
                            ? '#e0e7ff'
                            : n.role === 'UNKNOWN_WALLET'
                            ? '#fef3c7'
                            : '#f8fafc'
                        }
                        stroke={
                          n.role === 'VASP_ENDPOINT'
                            ? '#818cf8'
                            : n.role === 'TOKEN_CONTRACT'
                            ? '#94a3b8'
                            : n.role === 'NON_VASP_ENTITY'
                            ? '#2dd4bf'
                            : n.role === 'STARTING'
                            ? '#818cf8'
                            : n.role === 'UNKNOWN_WALLET'
                            ? '#f59e0b'
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
                            : n.role === 'TOKEN_CONTRACT'
                            ? 'fill-slate-800'
                            : n.role === 'NON_VASP_ENTITY'
                            ? 'fill-teal-900'
                            : n.role === 'STARTING'
                            ? 'fill-indigo-900'
                            : n.role === 'UNKNOWN_WALLET'
                            ? 'fill-amber-900'
                            : 'fill-slate-700'
                        }`}
                      >
                        {n.entityLabel
                          ? n.entityLabel.substring(0, 14)
                          : n.walletStatus.substring(0, 14)}
                      </text>
                    </g>
                  </g>
                );
              })}
            </g>
          </svg>

          {/* Interactive Edge Hover Tooltip */}
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

                  {edge.hop.delta_t_seconds !== null && edge.hop.delta_t_seconds !== undefined && edge.hop.delta_t_seconds > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-slate-400 font-bold">INTERVAL (Δt):</span>
                      <span>{formatTimeInterval(edge.hop.delta_t_seconds)}</span>
                    </div>
                  )}

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
          <span>Click any node or transaction edge to inspect in the Inspector below.</span>
        </div>
        <div className="font-mono text-slate-400 text-[11px] flex items-center space-x-3">
          <span>LEFT-TO-RIGHT HOP PROGRESSION</span>
          <span>•</span>
          <span>DRAG TO PAN • SCROLL TO ZOOM</span>
        </div>
      </div>
    </div>
  );
};
