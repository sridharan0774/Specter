import React, { useState } from 'react';
import type { TracePathDetail } from '../types/api';
import { ChevronRight, ChevronDown, ChevronUp, Network } from 'lucide-react';

interface PathExplorerProps {
  paths: TracePathDetail[];
  selectedPathId: string;
  onSelectPath: (pathId: string) => void;
  onNavigateToGraph?: () => void;
}

export const PathExplorer: React.FC<PathExplorerProps> = ({
  paths,
  selectedPathId,
  onSelectPath,
  onNavigateToGraph,
}) => {
  const [showAll, setShowAll] = useState(false);

  if (!paths || paths.length === 0) return null;

  const displayPaths = showAll ? paths : paths.slice(0, 3);
  const hasMore = paths.length > 3;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs mb-6 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4 font-sans">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-900 font-sans">
            DISCOVERED TRACE PATHS ({paths.length})
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Ranked multi-hop execution routes. Select a path card to focus fund flow graph analysis.
          </p>
        </div>
        {hasMore && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="flex items-center space-x-1 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] font-sans transition-colors"
          >
            <span>{showAll ? 'Show Top 3 Paths Only' : `VIEW ALL ${paths.length} PATHS`}</span>
            {showAll ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      <div className="space-y-3 font-sans">
        {displayPaths.map((path, idx) => {
          const isSelected = path.path_id === selectedPathId;
          const rankNumber = String(idx + 1).padStart(2, '0');

          return (
            <div
              key={path.path_id}
              onClick={() => onSelectPath(path.path_id)}
              className={`p-4 rounded-md border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-indigo-50/60 border-[#3730A3] shadow-xs ring-1 ring-[#3730A3]'
                  : 'bg-slate-50/50 border-slate-200 hover:bg-slate-100/50 hover:border-slate-300'
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Left Rank & Address Hop Sequence */}
                <div className="flex items-start space-x-3">
                  <span
                    className={`font-mono text-xs font-bold px-2 py-1 rounded border ${
                      isSelected
                        ? 'bg-[#3730A3] text-white border-[#3730A3]'
                        : 'bg-slate-200/80 text-slate-700 border-slate-300'
                    }`}
                  >
                    PATH #{rankNumber}
                  </span>

                  <div className="space-y-1.5">
                    {/* Wallet Chain Sequence */}
                    <div className="flex items-center space-x-1.5 flex-wrap font-mono text-xs font-semibold text-slate-900">
                      {path.wallet_sequence.map((addr, wIdx) => {
                        const isLast = wIdx === path.wallet_sequence.length - 1;
                        const isFirst = wIdx === 0;
                        return (
                          <React.Fragment key={wIdx}>
                            <span
                              className={`px-1.5 py-0.5 rounded ${
                                isFirst
                                  ? 'bg-indigo-100/80 text-[#3730A3] font-bold'
                                  : isLast
                                  ? 'bg-slate-900 text-white font-bold'
                                  : 'bg-slate-200/70 text-slate-800'
                              }`}
                            >
                              {addr.length > 10 ? `${addr.substring(0, 4)}...${addr.substring(addr.length - 4)}` : addr}
                            </span>
                            {!isLast && <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                          </React.Fragment>
                        );
                      })}
                    </div>

                    {/* Explanatory notes */}
                    {path.relevance_explanation && path.relevance_explanation.length > 0 && (
                      <div className="text-xs font-sans text-slate-600 space-y-0.5 pt-0.5">
                        {path.relevance_explanation.map((exp, expIdx) => (
                          <div key={expIdx} className="flex items-center space-x-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#3730A3] inline-block" />
                            <span>{exp}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Tabular Metrics Matrix & CTA */}
                <div className="flex items-center justify-between lg:justify-end gap-4 border-t lg:border-t-0 lg:border-l border-slate-200 pt-3 lg:pt-0 lg:pl-4 text-xs font-sans">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-[10px] font-sans font-medium text-slate-500 uppercase">HOPS</div>
                      <div className="text-xs font-bold text-slate-900 font-mono tabular-nums">{path.hop_count} Hops</div>
                    </div>

                    <div>
                      <div className="text-[10px] font-sans font-medium text-slate-500 uppercase">RETENTION</div>
                      <div className="text-xs font-bold text-emerald-800 font-mono tabular-nums">
                        {path.value_retention_percent.toFixed(1)}%
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] font-sans font-medium text-slate-500 uppercase">RELEVANCE</div>
                      <div className="text-xs font-bold text-[#3730A3] font-mono tabular-nums">
                        {path.relevance_score.toFixed(0)}/100
                      </div>
                    </div>
                  </div>

                  {onNavigateToGraph && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectPath(path.path_id);
                        onNavigateToGraph();
                      }}
                      className="flex items-center space-x-1 px-3 py-1.5 bg-white hover:bg-slate-50 text-[#3730A3] font-semibold border border-slate-200 rounded-md text-[11px] font-sans shadow-xs transition-colors flex-shrink-0"
                    >
                      <Network className="w-3.5 h-3.5 text-[#3730A3]" />
                      <span>INSPECT GRAPH</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
