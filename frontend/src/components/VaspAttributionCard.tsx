import React, { useState } from 'react';
import type { VASPAttributionResponse } from '../types/api';
import { Building2, CheckCircle2, AlertTriangle, ExternalLink, FileCheck, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';

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
  const isResolved = vaspData?.status === 'RESOLVED';
  const hasHighConfidence = vaspData?.has_high_confidence_match ?? isResolved;

  // NEGATIVE RESULT STATE
  if (!vaspData || !hasHighConfidence || candidates.length === 0) {
    const targetWallet = vaspData?.target_wallet || vaspData?.starting_wallet || 'N/A';
    const chain = vaspData?.chain || 'TRON';
    const asset = vaspData?.asset || 'USDT';
    const walletsCount = vaspData?.wallets_traced_count ?? 0;
    const txCount = vaspData?.transactions_traced_count ?? 0;
    const candidateCount = vaspData?.candidates_considered_count ?? candidates.length;
    const knownMatches = vaspData?.known_endpoint_matches && vaspData.known_endpoint_matches.length > 0
      ? vaspData.known_endpoint_matches
      : [];

    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-0.5">
              VASP ATTRIBUTION
            </div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans">
              Attribution Evaluation
            </h2>
          </div>
          <div className="flex items-center space-x-1.5 text-xs font-sans text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-md font-semibold">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
            <span>NO HIGH-CONFIDENCE VASP IDENTIFIED</span>
          </div>
        </div>

        {/* Primary Statement */}
        <div className="flex items-start space-x-3 text-amber-900 bg-amber-50/70 p-4 rounded-md border border-amber-200 mb-5">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900 font-sans">
              NO HIGH-CONFIDENCE VASP IDENTIFIED
            </h3>
            <p className="text-xs text-amber-800 font-sans leading-relaxed">
              The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP.
            </p>
            <p className="text-[11px] font-semibold text-amber-900/80 italic pt-0.5 font-sans">
              This is a valid investigation result.
            </p>
          </div>
        </div>

        {/* Investigation Context Ledger */}
        <div className="bg-slate-50 p-4 rounded-md border border-slate-200 mb-5">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-3 font-sans">
            Investigation Trace Context
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-sans">
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Target Wallet</span>
              <span className="font-mono text-slate-900 font-medium truncate block" title={targetWallet}>
                {targetWallet.length > 12 ? `${targetWallet.slice(0, 6)}...${targetWallet.slice(-4)}` : targetWallet}
              </span>
            </div>
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Network / Asset</span>
              <span className="font-mono text-slate-900 font-medium block">{chain} ({asset})</span>
            </div>
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Wallets Traced</span>
              <span className="font-mono text-slate-900 font-bold block tabular-nums">{walletsCount}</span>
            </div>
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Txs Analyzed</span>
              <span className="font-mono text-slate-900 font-bold block tabular-nums">{txCount}</span>
            </div>
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Candidates Evaluated</span>
              <span className="font-mono text-slate-900 font-bold block tabular-nums">{candidateCount}</span>
            </div>
            <div className="bg-white p-2.5 rounded border border-slate-200">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">Endpoint Matches</span>
              <span className="font-mono text-slate-900 font-medium block truncate" title={knownMatches.join(', ') || 'None'}>
                {knownMatches.length > 0 ? `${knownMatches.length} match(es)` : 'None'}
              </span>
            </div>
          </div>
        </div>

        {/* Reason Attribution Did Not Reach Confidence Threshold */}
        <div className="bg-slate-50 p-4 rounded-md border border-slate-200">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 mb-2 font-sans">
            Reason Attribution Did Not Reach Confidence Threshold
          </h4>
          <p className="text-xs text-slate-600 font-sans leading-relaxed">
            {vaspData?.negative_reason ||
              'The traced fund flow did not terminate at a known high-confidence VASP operational address. Traced paths concluded at unclassified private wallets or intermediate associations below the analytical confidence threshold.'}
          </p>
        </div>

        {/* Lower-Confidence or Intermediate Candidates Evaluated */}
        {candidates.length > 0 && (
          <div className="mt-5 pt-5 border-t border-slate-200">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 font-sans">
              Candidates Evaluated (Below Confidence Threshold)
            </h4>
            <div className="space-y-2">
              {candidates.map((cand, idx) => (
                <div key={idx} className="bg-slate-50 p-3 rounded-md border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-sans">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900">{cand.candidate_name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 font-medium uppercase">
                      {cand.match_position || 'INTERMEDIATE ASSOCIATION'}
                    </span>
                    <span className="text-slate-500 font-mono text-[11px]">{cand.endpoint_address}</span>
                  </div>
                  <div className="flex items-center space-x-4 text-slate-600 font-medium">
                    <span>{cand.endpoint_hop_distance} Hop(s)</span>
                    <span className="font-mono font-bold text-slate-800 tabular-nums">
                      Score: {cand.attribution_confidence.toFixed(1)}% ({cand.confidence_band})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // POSITIVE RESOLUTION STATE
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
            VASP ATTRIBUTION
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans">
            EVIDENCE-BACKED VASP ATTRIBUTION ({candidates.length} CANDIDATE{candidates.length > 1 ? 'S' : ''})
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Virtual Asset Service Providers (exchanges or custodial services) matched to traced fund flow endpoints.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-sans text-emerald-800 bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-md font-semibold">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>STATUS: LIKELY VASP ATTRIBUTION</span>
        </div>
      </div>

      <div className="space-y-6">
        {candidates.map((cand, idx) => {
          const rank = String(idx + 1).padStart(2, '0');
          const isExpanded = showTechnicalDetails[cand.endpoint_address + idx] || false;
          const isTerminal = cand.is_terminal_endpoint ?? (cand.match_position === 'TERMINAL_ENDPOINT');
          const whyItems = cand.why_this_vasp && cand.why_this_vasp.length > 0
            ? cand.why_this_vasp
            : (cand.matched_relevance_reasons || []);

          return (
            <div
              key={cand.endpoint_address + idx}
              className="bg-slate-50/60 border border-slate-200 rounded-lg p-5 transition-all hover:border-slate-300"
            >
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
                {/* Left: Main Entity & Metrics */}
                <div className="space-y-4 flex-1">
                  {/* Entity Name, Role, & Classification Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-sans text-xs font-semibold bg-[#3730A3] text-white px-2.5 py-0.5 rounded">
                      MATCH #{rank}
                    </span>
                    <h3 className="text-lg font-bold text-slate-900 tracking-tight flex items-center space-x-2 font-sans">
                      <Building2 className="w-5 h-5 text-[#3730A3]" />
                      <span>{cand.candidate_name}</span>
                    </h3>
                    <span className="text-[10px] font-sans uppercase bg-slate-200 text-slate-800 px-2 py-0.5 rounded font-semibold">
                      ROLE: {cand.entity_role || 'VASP'}
                    </span>
                    <span
                      className={`text-[10px] font-sans uppercase px-2 py-0.5 rounded font-semibold border ${
                        isTerminal
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border-amber-200'
                      }`}
                    >
                      {isTerminal ? 'TERMINAL ENDPOINT' : 'INTERMEDIATE ASSOCIATION'}
                    </span>
                  </div>

                  {/* Matched Address Strip */}
                  <div
                    onClick={() => onSelectNode && onSelectNode(cand.endpoint_address)}
                    className="flex items-center space-x-2 text-xs text-slate-700 bg-white p-2.5 rounded-md border border-slate-200 cursor-pointer hover:border-indigo-300 transition-colors"
                  >
                    <span className="text-slate-400 uppercase font-sans font-semibold text-[10px]">
                      MATCHED ADDRESS:
                    </span>
                    <span className="font-mono font-medium text-slate-900">{cand.endpoint_address}</span>
                    <a
                      href={`https://tronscan.org/#/address/${cand.endpoint_address}`}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-[#2563EB] hover:text-[#1d4ed8] ml-auto flex items-center space-x-1 font-sans"
                    >
                      <span className="text-[11px] font-medium">TRONSCAN</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  {/* Comprehensive 4-Column Attribute Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-sans">
                    <div className="bg-white p-2.5 rounded border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Endpoint / Position</span>
                      <span className="font-bold text-slate-900 block mt-0.5">
                        {isTerminal ? 'Terminal Endpoint' : 'Intermediate Relay'}
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Hop Distance</span>
                      <span className="font-bold text-slate-900 block mt-0.5">
                        {cand.endpoint_hop_distance} Hop{cand.endpoint_hop_distance !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Value Continuity</span>
                      <span className="font-bold text-slate-900 font-mono block mt-0.5 tabular-nums">
                        {cand.value_retention_percent != null
                          ? `${cand.value_retention_percent.toFixed(1)}%`
                          : 'Preserved'}
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">Source Quality</span>
                      <span className="font-bold text-slate-900 block mt-0.5">
                        Level {cand.source_metadata?.source_quality_level ?? 3} ({cand.source_metadata?.source || 'Verified'})
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right: Confidence Score & Metrics */}
                <div className="w-full lg:w-80 bg-white p-4 rounded-md border border-slate-200 space-y-4">
                  <div>
                    <div className="flex justify-between items-center text-xs mb-1 font-sans">
                      <span className="text-slate-600 font-semibold text-[11px]">
                        Attribution Confidence:
                      </span>
                      <span className="font-mono font-bold text-[#3730A3] tabular-nums text-sm">
                        {cand.attribution_confidence.toFixed(1)}%
                      </span>
                    </div>
                    {/* Horizontal Confidence Bar */}
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200">
                      <div
                        className="bg-[#3730A3] h-full rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, cand.attribution_confidence))}%` }}
                      />
                    </div>
                    <div className="flex justify-between items-center text-[10px] text-slate-400 mt-1 font-sans">
                      <span>Threshold: 70.0%</span>
                      <span className="font-semibold text-slate-700 uppercase">{cand.confidence_band} CONFIDENCE</span>
                    </div>
                  </div>

                  {/* Secondary Metrics */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs font-sans">
                    <div className="bg-slate-50 p-2 rounded-md border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Source Confidence</div>
                      <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                        {(cand.source_confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-md border border-slate-200">
                      <div className="text-[10px] text-slate-500 font-medium">Traced Paths</div>
                      <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                        {cand.path_convergence_count ?? 1} Converging
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* WHY THIS VASP? Section */}
              {whyItems.length > 0 && (
                <div className="mt-5 pt-4 border-t border-slate-200">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center space-x-1.5 font-sans">
                    <FileCheck className="w-4 h-4 text-[#3730A3]" />
                    <span>WHY THIS VASP?</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-700 font-sans">
                    {whyItems.map((reason, rIdx) => {
                      const cleanReason = reason.startsWith('✓') ? reason.slice(1).trim() : reason;
                      return (
                        <div key={rIdx} className="flex items-start space-x-2 bg-white p-2.5 rounded-md border border-slate-200">
                          <span className="text-[#3730A3] font-bold font-mono text-[11px] mt-0.5">•</span>
                          <span className="leading-snug">{cleanReason}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Collapsible Technical Details */}
              <div className="mt-4 pt-3 border-t border-slate-200">
                <button
                  onClick={() => toggleDetails(cand.endpoint_address + idx)}
                  className="flex items-center space-x-1.5 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] transition-colors font-sans"
                >
                  <span>{isExpanded ? 'Hide Technical Audit Trail' : 'VIEW TECHNICAL AUDIT TRAIL'}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-3 bg-white p-4 rounded-md border border-slate-200 space-y-3 text-xs text-slate-700 font-sans">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-semibold block">Attribution Classification</span>
                        <span className="font-mono font-bold text-slate-900">{cand.attribution_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-semibold block">Source Reference</span>
                        <span className="font-mono text-slate-900">{cand.source_metadata?.source_reference || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-semibold block">Source URL</span>
                        {cand.source_metadata?.source_url ? (
                          <a
                            href={cand.source_metadata.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[#2563EB] hover:underline font-mono truncate block"
                          >
                            {cand.source_metadata.source_url}
                          </a>
                        ) : (
                          <span className="text-slate-500 font-mono">N/A</span>
                        )}
                      </div>
                    </div>

                    {/* Factual Score Component Breakdown */}
                    {cand.score_components && Object.keys(cand.score_components).length > 0 && (
                      <div className="pt-2 border-t border-slate-100">
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-slate-400 text-[10px] uppercase font-semibold block">
                            Score Component Breakdown (Total: {cand.attribution_confidence.toFixed(1)} / 100.0)
                          </span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-sans">
                          {Object.entries(cand.score_components).map(([key, pts]) => (
                            <div key={key} className="bg-slate-50 p-2 rounded border border-slate-200">
                              <span className="text-[10px] text-slate-500 font-medium block capitalize">
                                {key.replace(/_/g, ' ')}
                              </span>
                              <span className="font-mono font-bold text-slate-900 tabular-nums">
                                +{Number(pts).toFixed(1)} pts
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {cand.path_sequence && cand.path_sequence.length > 0 && (
                      <div className="pt-2 border-t border-slate-100">
                        <span className="text-slate-400 text-[10px] uppercase font-semibold block mb-1">
                          Path Address Sequence
                        </span>
                        <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-slate-800">
                          {cand.path_sequence.map((addr, pIdx) => (
                            <React.Fragment key={pIdx}>
                              <span className="bg-slate-100 px-2 py-0.5 rounded border border-slate-200">{addr}</span>
                              {pIdx < (cand.path_sequence?.length || 0) - 1 && (
                                <span className="text-slate-400 font-sans font-bold">→</span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>
                    )}

                    {cand.supporting_transactions && cand.supporting_transactions.length > 0 && (
                      <div className="pt-2 border-t border-slate-100">
                        <span className="text-slate-400 text-[10px] uppercase font-semibold block mb-1">
                          Supporting Transaction Hashes ({cand.supporting_transactions.length})
                        </span>
                        <div className="space-y-1 font-mono text-[11px] text-slate-700 max-h-24 overflow-y-auto">
                          {cand.supporting_transactions.map((tx, tIdx) => (
                            <div key={tIdx} className="truncate">
                              <a
                                href={`https://tronscan.org/#/transaction/${tx}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[#2563EB] hover:underline"
                              >
                                {tx}
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 italic">
                      Disclaimer: Analytical attribution based on on-chain fund transfer topology and verified intelligence registries. Does not constitute legal proof of beneficial ownership or control.
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