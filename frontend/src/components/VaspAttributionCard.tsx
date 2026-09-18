import React, { useState } from 'react';
import type { VASPAttributionResponse } from '../types/api';
import { Building2, CheckCircle2, AlertTriangle, ExternalLink, FileCheck, ChevronDown, ChevronUp } from 'lucide-react';

interface VaspAttributionCardProps {
  vaspData?: VASPAttributionResponse;
  onSelectNode?: (address: string) => void;
}

export const VaspAttributionCard: React.FC<VaspAttributionCardProps> = ({ vaspData, onSelectNode }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<Record<string, boolean>>({});

  const toggleDetails = (addr: string) => {
    setShowTechnicalDetails((prev) => ({ ...prev, [addr]: !prev[addr] }));
  };

  const candidates = vaspData?.candidates || [];
  const hasHighConfidence = vaspData?.has_high_confidence_match ?? (candidates.length > 0 && (candidates[0].attribution_confidence >= 40));

  if (!vaspData || candidates.length === 0 || !hasHighConfidence) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
          LIKELY VASP
        </div>
        <div className="flex items-center space-x-3 text-amber-800 bg-amber-50/60 p-4 rounded-md border border-amber-200 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-900 font-sans">
              No High-Confidence VASP Identified (&lt;40% Confidence)
            </h3>
            <p className="text-xs text-amber-800 font-sans mt-0.5">
              The downstream endpoints do not match known high-confidence VASP infrastructure clusters with sufficient statistical certainty.
            </p>
          </div>
        </div>

        <div className="bg-slate-50 p-4 rounded-md border border-slate-200">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2 font-sans">
            Missing Information Checklist for VASP Resolution
          </h4>
          <ul className="text-xs text-slate-600 space-y-1.5 font-sans">
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              <span>Downstream hop count limit reached before reaching hot/cold exchange wallet clusters.</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              <span>Target wallet address not linked to published VASP deposit tag directory.</span>
            </li>
            <li className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              <span>Sweeper contract or mixer interaction detected requiring deeper graph unrolling.</span>
            </li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
            LIKELY VASP
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans">
            LIKELY VASP IDENTIFIED ({candidates.length} CANDIDATES)
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Virtual Asset Service Providers (exchanges or custodial services) matched to downstream receiving wallets.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-sans text-emerald-800 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-md font-semibold">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>STATUS: {vaspData.resolution_status}</span>
        </div>
      </div>

      <div className="space-y-6">
        {candidates.map((cand, idx) => {
          const rank = String(idx + 1).padStart(2, '0');
          const isExpanded = showTechnicalDetails[cand.endpoint_address + idx] || false;

          return (
            <div
              key={cand.endpoint_address + idx}
              className="bg-slate-50/60 border border-slate-200 rounded-lg p-5 transition-all hover:border-slate-300"
            >
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
                {/* Horizontal Rank Strip & Main Details */}
                <div className="space-y-3 flex-1">
                  <div className="flex items-center space-x-3">
                    <span className="font-sans text-xs font-semibold bg-[#3730A3] text-white px-2.5 py-0.5 rounded">
                      MATCH #{rank}
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 tracking-tight flex items-center space-x-2 font-sans">
                      <Building2 className="w-5 h-5 text-[#3730A3]" />
                      <span>{cand.candidate_name}</span>
                    </h3>
                    <span className="text-[10px] font-sans uppercase bg-indigo-50 text-[#3730A3] px-2 py-0.5 rounded border border-indigo-200 font-semibold">
                      {cand.attribution_type}
                    </span>
                  </div>

                  {/* Verifiable Endpoint Address */}
                  <div
                    onClick={() => onSelectNode && onSelectNode(cand.endpoint_address)}
                    className="flex items-center space-x-2 text-xs text-slate-700 bg-white p-2.5 rounded-md border border-slate-200 cursor-pointer hover:border-indigo-300 transition-colors"
                  >
                    <span className="text-slate-400 uppercase font-sans font-semibold text-[10px]">
                      ENDPOINT ADDRESS:
                    </span>
                    <span className="font-mono font-medium text-slate-900">{cand.endpoint_address}</span>
                    <a
                      href={`https://tronscan.org/#/address/${cand.endpoint_address}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#2563EB] hover:text-[#1d4ed8] ml-auto flex items-center space-x-1 font-sans"
                    >
                      <span className="text-[11px] font-medium">TRONSCAN</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  {/* Evidence Summary */}
                  {cand.evidence_summary && (
                    <p className="text-xs text-slate-600 font-sans leading-relaxed pt-1">
                      {cand.evidence_summary}
                    </p>
                  )}
                </div>

                {/* Right: Confidence in VASP Match */}
                <div className="w-full lg:w-80 bg-white p-4 rounded-md border border-slate-200 space-y-4">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1 font-sans">
                      <span className="text-slate-600 font-semibold text-[11px]">
                        Confidence in VASP Match:
                      </span>
                      <span className="font-mono font-bold text-[#3730A3] tabular-nums">
                        {cand.attribution_confidence.toFixed(1)}%
                      </span>
                    </div>
                    {/* SLIM HORIZONTAL CONFIDENCE BAR */}
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                      <div
                        className="bg-[#3730A3] h-full rounded-full"
                        style={{ width: `${cand.attribution_confidence}%` }}
                      />
                    </div>
                  </div>

                  {/* Plain Language Metric Cards */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs font-sans">
                    <div className="bg-slate-50 p-2 rounded-md border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Source Reliability</div>
                      <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                        {cand.source_confidence.toFixed(1)}%
                      </div>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-md border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Distance to VASP</div>
                      <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                        {cand.endpoint_hop_distance} Hops
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* WHY THIS VASP MATCH Section */}
              {cand.matched_relevance_reasons && cand.matched_relevance_reasons.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-200">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 flex items-center space-x-1.5 font-sans">
                    <FileCheck className="w-3.5 h-3.5 text-[#3730A3]" />
                    <span>Why This VASP Match</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-700 font-sans">
                    {cand.matched_relevance_reasons.map((reason, rIdx) => (
                      <div key={rIdx} className="flex items-start space-x-2 bg-white p-2 rounded-md border border-slate-200">
                        <span className="text-[#3730A3] font-bold font-mono text-[11px]">•</span>
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Collapsible Technical Details */}
              <div className="mt-3 pt-3 border-t border-slate-200">
                <button
                  onClick={() => toggleDetails(cand.endpoint_address + idx)}
                  className="flex items-center space-x-1.5 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] transition-colors font-sans"
                >
                  <span>{isExpanded ? 'Hide Technical Details' : 'VIEW DETAILS'}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-3 bg-white p-4 rounded-md border border-slate-200 space-y-2 text-xs text-slate-700 font-sans">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-slate-500 text-[10px] block font-sans">ATTRIBUTION TYPE:</span>
                        <span className="font-mono font-bold text-slate-900">{cand.attribution_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block font-sans">RAW HOP DISTANCE:</span>
                        <span className="font-mono font-bold text-slate-900">{cand.endpoint_hop_distance}</span>
                      </div>
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