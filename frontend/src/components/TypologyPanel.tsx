import React, { useState } from 'react';
import type { TypologyAnalysisResponse } from '../types/api';
import { Layers, ChevronDown, ChevronUp } from 'lucide-react';

interface TypologyPanelProps {
  typologyData?: TypologyAnalysisResponse;
}

export const TypologyPanel: React.FC<TypologyPanelProps> = ({ typologyData }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<Record<string, boolean>>({});

  const toggleDetails = (typId: string) => {
    setShowTechnicalDetails((prev) => ({ ...prev, [typId]: !prev[typId] }));
  };

  const typologies = typologyData?.typologies || [];

  if (!typologyData || typologies.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
        <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 font-sans">
          <Layers className="w-4 h-4 text-slate-400" />
          <span>MOVEMENT PATTERN</span>
        </div>
        <p className="text-xs text-slate-500 font-sans">
          No complex money-laundering movement patterns (e.g., peel chains, rapid splitting, or layering) were detected.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
            MOVEMENT PATTERN
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans">
            DETECTED MOVEMENT PATTERNS ({typologies.length})
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Identifies known money-laundering behavior patterns such as peel chains, layering, or rapid splitting.
          </p>
        </div>
        <div className="text-xs font-sans text-[#3730A3] bg-indigo-50 border border-indigo-200 px-3 py-1 rounded-md font-semibold">
          STATUS: {typologyData.status}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {typologies.map((typ) => {
          const isExpanded = showTechnicalDetails[typ.typology_id] || false;

          return (
            <div
              key={typ.typology_id}
              className="bg-slate-50/60 border border-slate-200 rounded-md p-5 flex flex-col justify-between space-y-4 shadow-xs hover:border-slate-300 transition-colors"
            >
              <div className="space-y-3 font-sans">
                <div className="flex items-center justify-between">
                  <span className="font-sans text-xs font-semibold text-slate-900 uppercase">
                    PATTERN: {typ.typology_name.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[10px] font-semibold bg-indigo-50 text-[#3730A3] px-2 py-0.5 rounded border border-indigo-200 font-sans uppercase">
                    {typ.severity} SEVERITY
                  </span>
                </div>

                {/* One-Line Plain Investigator Explanation */}
                <div className="bg-white p-3 rounded-md border border-slate-200">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
                    Pattern Interpretation
                  </div>
                  <p className="text-xs text-slate-700 font-sans leading-relaxed">
                    {typ.description}
                  </p>
                </div>
              </div>

              {/* Investigator Metrics Breakdown */}
              <div className="grid grid-cols-3 gap-2 text-xs pt-2 border-t border-slate-200 font-sans">
                <div className="bg-white p-2 rounded-md border border-slate-200">
                  <div className="text-[10px] text-slate-500 font-medium font-sans uppercase">HOPS</div>
                  <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                    {typ.metrics.hop_count || 0} Hops
                  </div>
                </div>

                <div className="bg-white p-2 rounded-md border border-slate-200">
                  <div className="text-[10px] text-slate-500 font-medium font-sans uppercase">RETAINED</div>
                  <div className="text-sm font-bold text-emerald-800 font-mono tabular-nums">
                    {typ.metrics.value_retention_percent ? `${typ.metrics.value_retention_percent.toFixed(1)}%` : 'N/A'}
                  </div>
                </div>

                <div className="bg-white p-2 rounded-md border border-slate-200">
                  <div className="text-[10px] text-slate-500 font-medium font-sans uppercase">CONFIDENCE</div>
                  <div className="text-sm font-bold text-[#3730A3] font-mono tabular-nums">
                    {Math.round(typ.confidence * 100)}%
                  </div>
                </div>
              </div>

              {/* Collapsible Technical Details */}
              <div className="pt-2 border-t border-slate-200">
                <button
                  onClick={() => toggleDetails(typ.typology_id)}
                  className="flex items-center space-x-1.5 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] transition-colors font-sans"
                >
                  <span>{isExpanded ? 'Hide Technical Details' : 'VIEW DETAILS'}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-2 bg-white p-3 rounded-md border border-slate-200 space-y-2 text-xs text-slate-700 font-sans">
                    <div>
                      <span className="text-slate-500 text-[10px] block font-sans">TYPOLOGY CODE:</span>
                      <span className="font-mono font-bold text-slate-900">{typ.typology_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] block font-sans">RAW CONFIDENCE RATING:</span>
                      <span className="font-mono font-bold text-[#3730A3]">{typ.confidence.toFixed(4)}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};