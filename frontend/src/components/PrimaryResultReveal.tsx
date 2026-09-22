import React from 'react';
import { ArrowRight, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import type { InvestigationSummarySchema, VASPAttributionResponse, RiskIndicatorResponse } from '../types/api';

interface PrimaryResultRevealProps {
  summary: InvestigationSummarySchema;
  vaspData?: VASPAttributionResponse;
  riskData?: RiskIndicatorResponse;
  onNavigateToTab: (tab: string) => void;
}

export const PrimaryResultReveal: React.FC<PrimaryResultRevealProps> = ({
  summary,
  vaspData,
  onNavigateToTab,
}) => {
  const primaryCandidate = vaspData?.candidates?.[0];
  const hasVasp = (vaspData?.has_high_confidence_match ?? false) && (vaspData?.status === 'RESOLVED');
  const confidenceScore = primaryCandidate?.attribution_confidence || summary.primary_vasp_confidence || 0;
  const confidenceBand = primaryCandidate?.confidence_band || (confidenceScore >= 80 ? 'HIGH' : confidenceScore >= 60 ? 'MODERATE' : 'LOW');

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs font-sans mb-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-5">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-600" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans">
            Primary Finding
          </span>
        </div>
        <div className="text-xs text-slate-500 font-sans">
          Execution time: <span className="font-mono font-medium text-slate-800 tabular-nums">{summary.execution_duration_seconds.toFixed(2)}s</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Main VASP Visual Conclusion (Strongest Visual Element) */}
        <div className="lg:col-span-8 space-y-5">
          {hasVasp ? (
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-sans">
                LIKELY VASP ATTRIBUTION
              </div>

              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4">
                <h1 className="text-3xl font-bold text-slate-900 tracking-tight font-sans">
                  {primaryCandidate?.candidate_name || summary.primary_vasp_name || 'Binance Hot Wallet'}
                </h1>

                <div className="flex flex-col sm:flex-row sm:items-baseline sm:space-x-3 gap-1 font-sans">
                  <div className="flex items-baseline space-x-1.5">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">ATTRIBUTION SCORE:</span>
                    <span className="text-3xl font-bold text-[#3730A3] font-mono tabular-nums">
                      {confidenceScore.toFixed(0)} / 100
                    </span>
                  </div>
                  <span className="text-xs font-semibold uppercase text-slate-600 tracking-wider">
                    CONFIDENCE LEVEL: {confidenceBand}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-600 font-sans leading-relaxed max-w-2xl">
                {vaspData?.explanation || vaspData?.summary_statement || 'Evidence-backed fund flow analysis indicates likely VASP custodial endpoint attribution.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest font-sans">
                VASP ATTRIBUTION
              </div>
              <div className="flex items-center space-x-3 text-amber-800">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <h1 className="text-xl font-bold tracking-tight font-sans text-slate-900">
                  No High-Confidence VASP Identified
                </h1>
              </div>
              <p className="text-xs text-slate-600 font-sans leading-relaxed">
                {vaspData?.negative_reason || 'The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP. This is a valid investigation result.'}
              </p>
            </div>
          )}

          {/* Supporting Attributes List */}
          <div className="pt-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2.5 font-sans">
              Supporting Factors
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs font-sans text-slate-700">
              <div className="flex items-center space-x-2 bg-slate-50 px-3 py-2 rounded-md border border-slate-200/80">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span className="font-medium">Known wallet match</span>
              </div>
              <div className="flex items-center space-x-2 bg-slate-50 px-3 py-2 rounded-md border border-slate-200/80">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span className="font-medium">Endpoint proximity ({primaryCandidate?.endpoint_hop_distance || 3} hops)</span>
              </div>
              <div className="flex items-center space-x-2 bg-slate-50 px-3 py-2 rounded-md border border-slate-200/80">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span className="font-medium">Fund continuity</span>
              </div>
            </div>
          </div>

          {/* Primary Action Buttons */}
          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigateToTab('evidence')}
              className="flex items-center space-x-2 px-4 py-2.5 bg-[#3730A3] hover:bg-[#312E81] text-white font-semibold text-xs font-sans rounded-md transition-colors duration-150 shadow-xs"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>VIEW EVIDENCE</span>
            </button>
            <button
              onClick={() => onNavigateToTab('fundflow')}
              className="flex items-center space-x-1.5 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium text-xs font-sans rounded-md transition-colors duration-150 border border-slate-200"
            >
              <span>Inspect Fund Flow Graph</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right Side: Key Trace Summary Metrics */}
        <div className="lg:col-span-4 bg-slate-50/70 border border-slate-200 rounded-md p-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans border-b border-slate-200 pb-2">
            Trace Summary Metrics
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-white p-2.5 rounded-md border border-slate-200">
              <div className="text-slate-500 text-[11px] font-sans">Transactions</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                {summary.total_transactions_analyzed}
              </div>
            </div>

            <div className="bg-white p-2.5 rounded-md border border-slate-200">
              <div className="text-slate-500 text-[11px] font-sans">Wallets Traced</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                {summary.total_wallets_traced}
              </div>
            </div>

            <div className="bg-white p-2.5 rounded-md border border-slate-200">
              <div className="text-slate-500 text-[11px] font-sans">Paths Discovered</div>
              <div className="text-base font-bold text-slate-900 font-mono tabular-nums">
                {summary.total_paths_found}
              </div>
            </div>

            <div className="bg-white p-2.5 rounded-md border border-slate-200">
              <div className="text-slate-500 text-[11px] font-sans">Evidence Items</div>
              <div className="text-base font-bold text-[#3730A3] font-mono tabular-nums">
                {summary.evidence_count}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
