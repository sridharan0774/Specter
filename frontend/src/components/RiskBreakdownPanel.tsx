import React, { useState } from 'react';
import type { RiskIndicatorResponse } from '../types/api';
import { CheckCircle2, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';

interface RiskBreakdownPanelProps {
  riskData?: RiskIndicatorResponse;
}

export const RiskBreakdownPanel: React.FC<RiskBreakdownPanelProps> = ({ riskData }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!riskData) return null;

  const rawScore = riskData.raw_risk_score ?? 78.0;
  const contextualScore = riskData.contextual_risk_score ?? riskData.risk_score;
  const isServiceEntity = riskData.service_entity_context || riskData.is_known_service_entity;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
            OVERALL RISK
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>OVERALL RISK ASSESSMENT & RISK FACTORS</span>
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Evaluates structural movement speed, money retention, and verified entity context.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-sans font-semibold uppercase bg-amber-50 text-amber-900 border border-amber-200 px-3 py-1 rounded-md">
            RISK LEVEL: {riskData.risk_level}
          </span>
        </div>
      </div>

      {/* Primary Investigator Summary Box */}
      <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200 mb-6">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
          Investigator Risk Summary
        </div>
        <p className="text-xs text-slate-700 font-sans leading-relaxed">
          {riskData.risk_level === 'HIGH' || riskData.risk_level === 'CRITICAL' ? (
            <>
              This transaction sequence shows <span className="font-semibold text-amber-800">high structural risk</span> due to unusually fast transfer speed across multiple wallets combined with direct movement toward an exchange endpoint.
            </>
          ) : (
            <>
              This transaction sequence has been analyzed for speed, hop distance, and entity context. The overall risk level is calculated as <span className="font-semibold">{riskData.risk_level}</span>.
            </>
          )}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Primary Risk Level vs Base Suspicion */}
        <div className="space-y-4 font-sans">
          <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200 space-y-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-sans">
              Risk Level Summary
            </div>

            {/* Contextual Risk Score */}
            <div>
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs font-sans font-medium text-slate-700">CONTEXTUAL RISK:</span>
                <span className="font-mono text-xl font-bold text-[#3730A3] tabular-nums">
                  {contextualScore.toFixed(1)} <span className="text-xs text-slate-400 font-normal">/ 100</span>
                </span>
              </div>
              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden border border-slate-200">
                <div
                  className="bg-[#3730A3] h-full rounded-full"
                  style={{ width: `${contextualScore}%` }}
                />
              </div>
            </div>

            {/* Base Flow / Structural Risk Score */}
            <div className="pt-2 border-t border-slate-200">
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-xs font-sans font-medium text-slate-600">FLOW RISK / STRUCTURAL RISK:</span>
                <span className="font-mono text-sm font-bold text-slate-700 tabular-nums">
                  {rawScore.toFixed(1)} <span className="text-xs text-slate-400 font-normal">/ 100</span>
                </span>
              </div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-slate-400 h-full rounded-full"
                  style={{ width: `${rawScore}%` }}
                />
              </div>
            </div>

            {/* Entity Context Flag */}
            <div className="pt-2 flex items-center justify-between text-xs font-sans">
              <span className="text-slate-600 font-medium">ENTITY CONTEXT:</span>
              <span
                className={`font-semibold text-[11px] px-2 py-0.5 rounded border ${
                  isServiceEntity
                    ? 'bg-indigo-50 text-indigo-900 border-indigo-200'
                    : 'bg-slate-200/60 text-slate-700 border-slate-300'
                }`}
              >
                {isServiceEntity ? 'Verified VASP endpoint' : 'Unverified / Private wallet'}
              </span>
            </div>

            <div className="pt-2 text-[11px] text-slate-500 font-sans leading-relaxed border-t border-slate-200">
              Note: High structural flow indicators remain evidentiary; verified VASP context affects contextual risk assessment without implying transactions are lawful.
            </div>
          </div>
        </div>

        {/* Center/Right Col: Key Risk Factors & Safety Mitigations */}
        <div className="lg:col-span-2 space-y-4 font-sans">
          <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-sans mb-3">
              Key Risk Factors Identified
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs font-sans text-left">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-400 font-sans uppercase text-[10px]">
                    <th className="pb-2 font-semibold">RISK FACTOR</th>
                    <th className="pb-2 text-right font-semibold">WEIGHT CONTRIBUTION</th>
                    <th className="pb-2 text-right font-semibold">SCORE IMPACT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-slate-800 font-sans">
                  {Object.entries(riskData.component_contributions || {}).map(([key, val]) => (
                    <tr key={key}>
                      <td className="py-2.5 font-medium text-slate-700 font-sans">
                        {key
                          .replace(/_/g, ' ')
                          .replace(/velocity/gi, 'Movement Speed')
                          .replace(/retention/gi, 'Money Retained')
                          .replace(/proximity/gi, 'VASP Distance')
                          .toUpperCase()}
                      </td>
                      <td className="py-2.5 text-right font-bold font-mono tabular-nums">
                        {val.toFixed(1)} pts
                      </td>
                      <td className="py-2.5 text-right font-mono tabular-nums">
                        <span className="bg-indigo-50 text-[#3730A3] border border-indigo-200 px-2 py-0.5 rounded font-bold text-[11px]">
                          +{(val * 0.8).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Safety Mitigations Notes */}
          {riskData.false_positive_mitigations && riskData.false_positive_mitigations.length > 0 && (
            <div className="bg-emerald-50/60 border border-emerald-200 rounded-md p-4 space-y-2 font-sans">
              <div className="flex items-center space-x-2 text-emerald-900 font-semibold text-xs uppercase tracking-wider font-sans">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Safety Mitigation Applied</span>
              </div>
              <ul className="text-xs text-emerald-800 font-sans space-y-1">
                {riskData.false_positive_mitigations.map((note, nIdx) => (
                  <li key={nIdx} className="leading-relaxed">
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Collapsible Technical Computation Details */}
          <div className="pt-1 font-sans">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="flex items-center space-x-1.5 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] transition-colors font-sans"
            >
              <span>{showTechnicalDetails ? 'Hide Technical Details' : 'VIEW DETAILS'}</span>
              {showTechnicalDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showTechnicalDetails && (
              <div className="mt-3 bg-white p-4 rounded-md border border-slate-200 text-xs text-slate-700 space-y-2 font-sans">
                <div className="flex justify-between border-b border-slate-100 pb-1.5">
                  <span className="text-slate-500 font-sans">FLOW RISK / STRUCTURAL RISK:</span>
                  <span className="font-mono font-bold text-slate-900">{rawScore.toFixed(2)} / 100</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-1.5">
                  <span className="text-slate-500 font-sans">CONTEXTUAL RISK:</span>
                  <span className="font-mono font-bold text-[#3730A3]">{contextualScore.toFixed(2)} / 100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-sans">ENTITY CONTEXT:</span>
                  <span className="font-mono font-bold text-slate-900">{isServiceEntity ? 'Verified VASP endpoint' : 'Unverified / Private wallet'}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};