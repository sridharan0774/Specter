import React, { useState } from 'react';
import type { InvestigationSummarySchema, TraceResultResponse, VASPAttributionResponse } from '../types/api';
import { ShieldCheck, AlertCircle, Copy, Check, ExternalLink, Network, Layers, GitFork } from 'lucide-react';
import { buildAddressExplorerUrl, getExplorerName } from '../utils/explorer';

interface InvestigationStatusBarProps {
  summary?: InvestigationSummarySchema | null;
  traceData?: TraceResultResponse | null;
  vaspData?: VASPAttributionResponse | null;
  caseId?: string;
  chain?: string;
  maxHops?: number;
  status?: string;
}

export const InvestigationStatusBar: React.FC<InvestigationStatusBarProps> = ({
  summary,
  traceData,
  vaspData,
  caseId,
  chain,
  maxHops = 2,
  status = 'READY',
}) => {
  const [copied, setCopied] = useState(false);

  const effChain = chain || summary?.chain || traceData?.chain || 'TRON';
  const effAsset = summary?.asset || traceData?.asset || (effChain === 'BITCOIN' ? 'BTC' : 'USDT');
  const explorerName = getExplorerName(effChain);

  const startingWallet = traceData?.starting_wallet || summary?.target_wallet || '';
  const walletsTraced = traceData?.total_wallets_discovered ?? summary?.total_wallets_traced ?? 0;
  const pathsCount = traceData?.total_paths_found ?? summary?.total_paths_found ?? 0;
  const txCount = traceData?.total_transactions_analyzed ?? summary?.total_transactions_analyzed ?? 0;

  const topVasp = vaspData?.candidates?.[0];
  const hasVaspMatch = vaspData?.has_high_confidence_match || Boolean(topVasp && topVasp.attribution_confidence >= 40);

  const handleCopy = () => {
    if (!startingWallet) return;
    navigator.clipboard.writeText(startingWallet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const truncate = (addr: string) => {
    if (!addr || addr.length < 12) return addr;
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 6)}`;
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs font-sans">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Case & Status Indicator */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                status === 'COMPLETED'
                  ? 'bg-emerald-500'
                  : status === 'FAILED'
                  ? 'bg-red-500'
                  : status === 'TRACING' || status === 'GRAPH_ANALYSIS' || status === 'VASP_RESOLUTION'
                  ? 'bg-indigo-600 animate-ping'
                  : 'bg-slate-400'
              }`}
            />
            <span className="text-xs font-bold font-mono uppercase tracking-wider text-slate-900">
              {caseId || 'CASE-ACTIVE'}
            </span>
          </div>

          <span className="text-slate-300">|</span>

          {/* Status Badge */}
          <span
            className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold tracking-tight uppercase ${
              status === 'COMPLETED'
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : status === 'FAILED'
                ? 'bg-red-100 text-red-800 border border-red-300'
                : 'bg-indigo-100 text-indigo-800 border border-indigo-300'
            }`}
          >
            {status}
          </span>
        </div>

        {/* Center: Starting Wallet with One-Click Copy */}
        {startingWallet && (
          <div className="flex items-center space-x-2 text-xs font-mono bg-slate-50 px-3 py-1 rounded border border-slate-200">
            <span className="text-slate-500 font-sans font-medium text-[11px]">STARTING:</span>
            <span className="font-bold text-slate-800" title={startingWallet}>
              {truncate(startingWallet)}
            </span>
            <button
              onClick={handleCopy}
              className="text-slate-400 hover:text-slate-700 p-0.5 rounded transition-colors"
              title="Copy wallet address"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <a
              href={buildAddressExplorerUrl(startingWallet, effChain)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-indigo-600 p-0.5 rounded transition-colors"
              title={`View on ${explorerName}`}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        )}

        {/* Right: Tracing Metrics (Derived from Backend Only) */}
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1 text-slate-600">
            <span className="font-semibold text-slate-800 font-mono">{effChain}</span>
            <span className="text-slate-400">/</span>
            <span className="font-semibold text-slate-800 font-mono">{effAsset}</span>
          </div>

          <div className="flex items-center space-x-1 text-slate-600">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500">Depth:</span>
            <span className="font-mono font-bold text-slate-800">{maxHops} hops</span>
          </div>

          <div className="flex items-center space-x-1 text-slate-600">
            <Network className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500">Wallets:</span>
            <span className="font-mono font-bold text-slate-800">{walletsTraced}</span>
          </div>

          <div className="flex items-center space-x-1 text-slate-600">
            <GitFork className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500">Paths:</span>
            <span className="font-mono font-bold text-slate-800">{pathsCount}</span>
          </div>

          {txCount > 0 && (
            <div className="flex items-center space-x-1 text-slate-600">
              <span className="text-slate-500">Txs:</span>
              <span className="font-mono font-bold text-slate-800">{txCount}</span>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Sub-bar: VASP Attribution Resolution Summary */}
      <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs font-sans gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-slate-500 uppercase tracking-wider text-[10px] font-mono">
            VASP ATTRIBUTION:
          </span>
          {hasVaspMatch && topVasp ? (
            <div className="flex items-center space-x-2">
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-900 font-bold font-mono">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-700" />
                <span>{topVasp.candidate_name}</span>
              </span>
              <span className="text-slate-600 font-mono text-[11px]">
                Confidence: <strong className="text-indigo-700">{topVasp.attribution_confidence.toFixed(0)}/100 ({topVasp.confidence_band})</strong>
              </span>
              <span className="text-slate-400">•</span>
              <span className="text-slate-600 font-mono text-[11px]">
                Hop Distance: <strong>{topVasp.endpoint_hop_distance}</strong>
              </span>
              {topVasp.is_terminal_endpoint && (
                <span className="px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-mono font-semibold">
                  TERMINAL ENDPOINT
                </span>
              )}
            </div>
          ) : status === 'COMPLETED' ? (
            <div className="flex items-center space-x-1.5 text-slate-500">
              <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
              <span>No high-confidence VASP endpoint identified (Evidence score below threshold)</span>
            </div>
          ) : (
            <span className="text-slate-400 italic">Attribution pending investigation completion</span>
          )}
        </div>

        <div className="text-[11px] text-slate-400 font-mono">
          OPERATIONAL SCOPE: {effChain} {effAsset}
        </div>
      </div>
    </div>
  );
};

