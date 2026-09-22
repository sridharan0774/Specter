import React from 'react';
import type { VelocityAnalysisResponse, TypologyAnalysisResponse } from '../types/api';
import { AlertOctagon, ArrowRight } from 'lucide-react';
import { formatTimeInterval, formatCurrency } from '../utils/formatters';

interface SuspiciousAlertsBannerProps {
  velocityData?: VelocityAnalysisResponse;
  typologyData?: TypologyAnalysisResponse;
  onViewTrace: () => void;
}

export const SuspiciousAlertsBanner: React.FC<SuspiciousAlertsBannerProps> = ({
  velocityData,
  typologyData,
  onViewTrace,
}) => {
  const alerts = velocityData?.alerts || [];
  const typologies = typologyData?.typologies || [];

  if (alerts.length === 0 && typologies.length === 0) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs mb-6 border-l-2 border-l-red-600 font-sans">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
        <div className="flex items-center space-x-2">
          <AlertOctagon className="w-4 h-4 text-red-600 flex-shrink-0" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-700 font-sans">
            Suspicious Activity Detected ({alerts.length + typologies.length})
          </h2>
        </div>
        <button
          onClick={onViewTrace}
          className="flex items-center space-x-1 text-xs font-semibold text-[#3730A3] hover:text-[#312E81] font-sans transition-colors"
        >
          <span>VIEW TRACE</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Velocity Alerts */}
        {alerts.map((alert) => (
          <div
            key={alert.alert_id}
            className="bg-slate-50/80 border border-slate-200 rounded-md p-3.5 flex items-center justify-between gap-3"
          >
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
                <span className="text-xs font-semibold text-slate-900 font-sans">
                  Rapid Movement Alert
                </span>
                <span className="text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.5 rounded font-sans uppercase">
                  {alert.severity}
                </span>
              </div>
              <p className="text-xs text-slate-600 font-sans">
                <span className="font-mono font-medium text-slate-900">{alert.transfer_count} transfers</span> · <span className="font-mono text-slate-800">Initial: {formatCurrency(alert.initial_transfer_amount ?? alert.total_amount)}</span> · <span className="font-mono text-slate-600">Downstream: {formatCurrency(alert.downstream_activity_amount ?? 0)}</span> · Fastest gap: <span className="font-mono font-medium text-slate-900">{alert.minimum_delta_t != null ? formatTimeInterval(alert.minimum_delta_t) : 'N/A'}</span>
              </p>
            </div>
            <button
              onClick={onViewTrace}
              className="text-[11px] font-semibold text-[#3730A3] bg-white border border-slate-200 px-2.5 py-1 rounded hover:bg-slate-100 flex-shrink-0 transition-colors font-sans"
            >
              [ VIEW TRACE ]
            </button>
          </div>
        ))}

        {/* Typology Alerts */}
        {typologies.map((typ) => (
          <div
            key={typ.typology_id}
            className="bg-slate-50/80 border border-slate-200 rounded-md p-3.5 flex items-center justify-between gap-3"
          >
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
                <span className="text-xs font-semibold text-slate-900 font-sans">
                  {typ.typology_name.replace(/_/g, ' ')}
                </span>
                <span className="text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded font-sans uppercase">
                  {typ.severity}
                </span>
              </div>
              <p className="text-xs text-slate-600 font-sans">
                <span className="font-mono font-medium text-slate-900">{typ.metrics.hop_count || 3} hops</span> · <span className="font-mono font-medium text-slate-900">{typ.metrics.value_retention_percent ? `${typ.metrics.value_retention_percent.toFixed(1)}%` : 'High'} retention</span>
              </p>
            </div>
            <button
              onClick={onViewTrace}
              className="text-[11px] font-semibold text-[#3730A3] bg-white border border-slate-200 px-2.5 py-1 rounded hover:bg-slate-100 flex-shrink-0 transition-colors font-sans"
            >
              [ VIEW TRACE ]
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
