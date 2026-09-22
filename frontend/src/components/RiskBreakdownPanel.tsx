import React from 'react';
import type { RiskIndicatorResponse, RiskIndicatorItem } from '../types/api';
import { CheckCircle2, ShieldAlert, ExternalLink, Info, AlertTriangle, Activity } from 'lucide-react';
import { buildExplorerUrl, getExplorerName } from '../utils/explorer';

interface RiskBreakdownPanelProps {
  riskData?: RiskIndicatorResponse;
}

const DIMENSION_CAPS: Record<string, { label: string; max: number }> = {
  entity_exposure: { label: 'Entity Exposure', max: 30 },
  temporal: { label: 'Temporal Signals', max: 25 },
  obfuscation: { label: 'Obfuscation Signals', max: 25 },
  graph_structure: { label: 'Graph Structure', max: 20 },
  value_flow: { label: 'Value Flow', max: 15 },
  behavioural: { label: 'Behavioural Signals', max: 15 },
};

export const RiskBreakdownPanel: React.FC<RiskBreakdownPanelProps> = ({ riskData }) => {
  if (!riskData) return null;

  const isInsufficient = riskData.assessment_status === 'INSUFFICIENT_EVIDENCE' || riskData.risk_score === null;
  const scoreVal = riskData.risk_score !== null && riskData.risk_score !== undefined ? riskData.risk_score : null;
  const isServiceEntity = riskData.service_entity_context || riskData.is_known_service_entity;
  const explorerName = getExplorerName(riskData.chain || 'TRON');


  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      {/* Panel Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-100 pb-4 mb-6 gap-3">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">
            EXPLAINABLE GRAPH RISK ENGINE ({riskData.calculation_version || 'EGRE_V1'})
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>EXPLAINABLE GRAPH RISK ASSESSMENT</span>
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Traceable, deterministic indicator scoring with correlation control and evidence-backed explainability.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {isInsufficient ? (
            <span className="text-xs font-sans font-semibold uppercase bg-slate-100 text-slate-700 border border-slate-300 px-3 py-1 rounded-md flex items-center space-x-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-slate-500" />
              <span>INSUFFICIENT EVIDENCE</span>
            </span>
          ) : (
            <span
              className={`text-xs font-sans font-semibold uppercase px-3 py-1 rounded-md border ${
                riskData.risk_level === 'VERY HIGH' || riskData.risk_level === 'HIGH' || riskData.risk_level === 'CRITICAL'
                  ? 'bg-amber-50 text-amber-900 border-amber-300'
                  : riskData.risk_level === 'MODERATE'
                  ? 'bg-blue-50 text-blue-900 border-blue-300'
                  : 'bg-emerald-50 text-emerald-900 border-emerald-300'
              }`}
            >
              RISK LEVEL: {riskData.risk_level}
            </span>
          )}
        </div>
      </div>

      {/* INSUFFICIENT EVIDENCE STATE BANNER */}
      {isInsufficient ? (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-5 mb-6 text-xs text-slate-700 space-y-2 font-sans">
          <div className="flex items-center space-x-2 text-slate-800 font-bold font-mono">
            <Info className="w-4 h-4 text-slate-500" />
            <span>INSUFFICIENT TRANSACTION HISTORY FOR GRAPH RISK ASSESSMENT</span>
          </div>
          <p className="leading-relaxed">
            {riskData.contextual_interpretation ||
              'Only one observable transaction was available. The available history is insufficient for reliable behavioural and graph risk assessment.'}
          </p>
          <div className="text-[11px] text-slate-500 italic">
            Note: Insufficient evidence is an assessment state, not a low risk rating. Further downstream activity is required to evaluate risk indicators.
          </div>
        </div>
      ) : (
        <>
          {/* Primary Summary Banner */}
          <div className="bg-slate-50/70 p-4 rounded-md border border-slate-200 mb-6">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
              Investigator Risk Assessment
            </div>
            <p className="text-xs text-slate-700 font-sans leading-relaxed">
              Calculated Explainable Risk Score: <strong className="font-mono text-indigo-900 text-sm">{scoreVal?.toFixed(1)} / 100</strong> ({riskData.risk_level} Risk Level).
              This rating is derived deterministically from {riskData.indicators?.length || 0} observable transaction graph indicators without LLM intervention.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
            {/* Left Col (4 cols): Risk Level & Dimension Scores */}
            <div className="lg:col-span-4 space-y-4 font-sans">
              <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200 space-y-4">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono">
                  RISK SCORE SUMMARY
                </div>

                {/* Main Contextual Score Bar */}
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xs font-sans font-semibold text-slate-800">FINAL RISK SCORE:</span>
                    <span className="font-mono text-xl font-bold text-indigo-900 tabular-nums">
                      {scoreVal?.toFixed(1)} <span className="text-xs text-slate-400 font-normal">/ 100</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden border border-slate-200">
                    <div
                      className={`h-full rounded-full ${
                        (scoreVal || 0) >= 75
                          ? 'bg-rose-600'
                          : (scoreVal || 0) >= 50
                          ? 'bg-amber-600'
                          : (scoreVal || 0) >= 25
                          ? 'bg-blue-600'
                          : 'bg-emerald-600'
                      }`}
                      style={{ width: `${Math.min(100, scoreVal || 0)}%` }}
                    />
                  </div>
                </div>

                {/* Dimension Scores Breakdown (Correlation Control) */}
                <div className="pt-3 border-t border-slate-200 space-y-2.5">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono flex items-center justify-between">
                    <span>DIMENSION SCORES (CAPPED)</span>
                    <span className="text-[10px] text-slate-400">CORRELATION CONTROL</span>
                  </div>

                  {Object.entries(DIMENSION_CAPS).map(([key, info]) => {
                    const score = riskData.dimension_scores?.[key] || 0.0;
                    const pct = Math.min(100, (score / info.max) * 100);
                    return (
                      <div key={key} className="text-xs space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="text-slate-600">{info.label}:</span>
                          <span className="font-mono font-semibold text-slate-800">
                            {score.toFixed(1)} / {info.max} pts
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${score > 0 ? 'bg-indigo-600' : 'bg-slate-300'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Entity Context Flag */}
                <div className="pt-2 flex items-center justify-between text-xs font-sans border-t border-slate-200">
                  <span className="text-slate-600 font-medium">ENTITY CONTEXT:</span>
                  <span
                    className={`font-semibold text-[11px] px-2 py-0.5 rounded border ${
                      isServiceEntity
                        ? 'bg-indigo-50 text-indigo-900 border-indigo-200'
                        : 'bg-slate-200/60 text-slate-700 border-slate-300'
                    }`}
                  >
                    {isServiceEntity ? 'Verified VASP Endpoint' : 'Unverified / Private Wallet'}
                  </span>
                </div>
              </div>
            </div>

            {/* Right Col (8 cols): EXPLAINABLE "WHY THIS RISK?" ITEMIZATION */}
            <div className="lg:col-span-8 space-y-4 font-sans">
              <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-mono mb-3 flex items-center space-x-1.5">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  <span>WHY THIS RISK? (ITEMIZED EVIDENCE-LINKED INDICATORS)</span>
                </div>

                {riskData.indicators && riskData.indicators.length > 0 ? (
                  <div className="space-y-3">
                    {riskData.indicators.map((ind: RiskIndicatorItem, idx: number) => (
                      <div key={idx} className="bg-white p-3.5 rounded-md border border-slate-200 space-y-2 text-xs">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-indigo-700 text-sm">
                              +{ind.contribution.toFixed(1)} pts
                            </span>
                            <span className="font-bold text-slate-900">{ind.indicator_name}</span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                                ind.classification === 'OBSERVED'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                  : ind.classification === 'HEURISTIC'
                                  ? 'bg-amber-50 text-amber-800 border-amber-300'
                                  : 'bg-indigo-50 text-indigo-800 border-indigo-300'
                              }`}
                            >
                              [{ind.classification}]
                            </span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                            {ind.dimension}
                          </span>
                        </div>

                        <div className="text-slate-600 space-y-1">
                          <div>
                            <span className="font-medium text-slate-700">Measured Value: </span>
                            <span className="font-mono font-semibold text-slate-900">{ind.observed_value}</span>
                          </div>
                          <div className="text-[11px] text-slate-500">
                            Detection Rule: {ind.detection_rule} ({ind.threshold_reference})
                          </div>
                        </div>

                        {/* Supporting Transaction Evidence Hashes */}
                        {ind.supporting_transactions && ind.supporting_transactions.length > 0 && (
                          <div className="pt-1.5 flex flex-wrap items-center gap-2 border-t border-slate-100 font-mono text-[11px]">
                            <span className="text-slate-400 font-sans font-medium text-[10px]">SUPPORTING TXS:</span>
                            {ind.supporting_transactions.map((txHash, hIdx) => (
                              <a
                                key={hIdx}
                                href={buildExplorerUrl(txHash, riskData.chain)}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-600 hover:text-indigo-800 underline flex items-center space-x-0.5"
                                title={`View on ${explorerName}`}
                              >
                                <span>{txHash.substring(0, 10)}...</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 italic p-3 bg-white rounded border border-slate-200">
                    No elevated risk indicators detected in current transaction sequence.
                  </div>
                )}
              </div>

              {/* Safety Mitigations Notes */}
              {riskData.false_positive_mitigations && riskData.false_positive_mitigations.length > 0 && (
                <div className="bg-emerald-50/60 border border-emerald-200 rounded-md p-4 space-y-2 font-sans">
                  <div className="flex items-center space-x-2 text-emerald-900 font-semibold text-xs uppercase tracking-wider font-sans">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Contextual Safety Mitigations Applied</span>
                  </div>
                  <ul className="text-xs text-emerald-800 font-sans space-y-1">
                    {riskData.false_positive_mitigations.map((note, nIdx) => (
                      <li key={nIdx} className="leading-relaxed">
                        • {note}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* STATUTORY INVESTIGATIVE DISCLAIMER */}
      <div className="pt-4 border-t border-slate-200 text-[11px] text-slate-500 font-sans leading-relaxed flex items-start space-x-2">
        <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
        <div>
          <strong className="font-semibold text-slate-700">Investigative Interpretation Notice: </strong>
          {riskData.contextual_interpretation ||
            'Risk indicators represent observed transaction and graph patterns. They do not by themselves establish criminal activity, ownership, or illicit intent.'}
        </div>
      </div>
    </div>
  );
};