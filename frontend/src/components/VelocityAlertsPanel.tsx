import React, { useState } from 'react';
import type { VelocityAnalysisResponse } from '../types/api';
import { Zap, AlertOctagon, ChevronDown, ChevronUp } from 'lucide-react';
import { formatCurrency, formatTimeInterval } from '../utils/formatters';

interface VelocityAlertsPanelProps {
  velocityData?: VelocityAnalysisResponse;
}

export const VelocityAlertsPanel: React.FC<VelocityAlertsPanelProps> = ({ velocityData }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<Record<string, boolean>>({});

  const toggleDetails = (alertId: string) => {
    setShowTechnicalDetails((prev) => ({ ...prev, [alertId]: !prev[alertId] }));
  };

  const alerts = velocityData?.alerts || [];

  if (!velocityData || alerts.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
        <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 font-sans">
          <Zap className="w-4 h-4 text-slate-400" />
          <span>SUSPICIOUS MOVEMENT</span>
        </div>
        <p className="text-xs text-slate-500 font-sans">
          No rapid movement or suspicious speed alerts were detected for this investigation.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-8 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-sans mb-1">
            SUSPICIOUS MOVEMENT
          </div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-900 font-sans">
            SUSPICIOUS MOVEMENT & SPEED ALERTS ({alerts.length})
          </h2>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Detects funds moving suspiciously fast across multiple wallets in very short time windows.
          </p>
        </div>
        <div className="text-xs font-sans text-amber-800 bg-amber-50 border border-amber-200 px-3 py-1 rounded-md font-semibold">
          STATUS: {velocityData.status}
        </div>
      </div>

      <div className="space-y-4">
        {alerts.map((alert) => {
          const isExpanded = showTechnicalDetails[alert.alert_id] || false;

          return (
            <div
              key={alert.alert_id}
              className="bg-slate-50/60 rounded-md border border-slate-200 border-l-2 border-l-amber-600 p-5 space-y-4 shadow-xs"
            >
              {/* Top Row: Investigator Summary */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2.5">
                  <AlertOctagon className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <h3 className="text-sm font-semibold text-slate-900 font-sans">
                    {alert.alert_type.replace(/_/g, ' ').replace(/TEMPORAL ACCELERATION/gi, 'Rapid Movement')}
                  </h3>
                  <span className="text-[10px] font-semibold bg-amber-50 text-amber-900 px-2 py-0.5 rounded border border-amber-200 uppercase font-sans">
                    {alert.severity} SEVERITY
                  </span>
                </div>
                <div className="text-xs font-sans text-slate-600">
                  Movement speed:{' '}
                  <span className="font-mono font-bold text-amber-900 tabular-nums">
                    {alert.velocity_score.toFixed(1)} / 100
                  </span>
                </div>
              </div>

              {/* Investigator Conclusion First */}
              <div className="bg-white p-3.5 rounded-md border border-slate-200 space-y-1">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-sans">
                  Investigator Finding Summary
                </div>
                <p className="text-xs text-slate-700 font-sans leading-relaxed">
                  {alert.explanation.replace(/temporal acceleration/gi, 'rapid movement')}
                </p>
              </div>

              {/* Investigator Key Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-sans pt-1">
                <div className="bg-white p-2.5 rounded-md border border-slate-200">
                  <div className="text-[11px] font-medium text-slate-500 font-sans">Transfers</div>
                  <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">{alert.transfer_count} Transfers</div>
                </div>

                <div className="bg-white p-2.5 rounded-md border border-slate-200">
                  <div className="text-[11px] font-medium text-slate-500 font-sans">Total Moved</div>
                  <div className="text-sm font-bold text-slate-900 font-mono tabular-nums">
                    {formatCurrency(alert.total_amount)}
                  </div>
                </div>

                <div className="bg-white p-2.5 rounded-md border border-slate-200">
                  <div className="text-[11px] font-medium text-slate-500 font-sans">Fastest Transfer Gap</div>
                  <div className="text-sm font-bold text-amber-800 font-mono tabular-nums">
                    {formatTimeInterval(alert.minimum_delta_t)}
                  </div>
                </div>

                <div className="bg-white p-2.5 rounded-md border border-slate-200">
                  <div className="text-[11px] font-medium text-slate-500 font-sans">Average Transfer Gap</div>
                  <div className="text-sm font-bold text-slate-800 font-mono tabular-nums">
                    {formatTimeInterval(alert.average_delta_t)}
                  </div>
                </div>
              </div>

              {/* Collapsible Technical Details */}
              <div className="pt-2 border-t border-slate-200">
                <button
                  onClick={() => toggleDetails(alert.alert_id)}
                  className="flex items-center space-x-1.5 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] transition-colors font-sans"
                >
                  <span>{isExpanded ? 'Hide Technical Details' : 'VIEW DETAILS'}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-3 bg-white p-4 rounded-md border border-slate-200 space-y-3 text-xs text-slate-700 font-sans">
                    <div className="grid grid-cols-2 gap-4 font-mono">
                      <div>
                        <span className="text-slate-500 text-[10px] block font-sans">EXACT MINIMUM Δt:</span>
                        <span className="font-bold text-slate-900">{alert.minimum_delta_t} seconds</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block font-sans">EXACT AVERAGE Δt:</span>
                        <span className="font-bold text-slate-900">{alert.average_delta_t} seconds</span>
                      </div>
                    </div>

                    {alert.reason_codes && alert.reason_codes.length > 0 && (
                      <div>
                        <span className="text-slate-500 text-[10px] block mb-1 font-sans">SYSTEM REASON CODES:</span>
                        <div className="flex flex-wrap gap-2 font-mono">
                          {alert.reason_codes.map((rc, rcIdx) => (
                            <span
                              key={rcIdx}
                              className="bg-slate-100 text-slate-800 border border-slate-200 px-2 py-0.5 rounded font-medium text-[11px]"
                            >
                              {rc}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
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