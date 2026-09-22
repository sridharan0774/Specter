import React from 'react';
import type { TraceHopItem } from '../types/api';
import { X, ExternalLink, ArrowRight, Layers } from 'lucide-react';
import { buildExplorerUrl, buildAddressExplorerUrl, getExplorerName } from '../utils/explorer';
import { formatCryptoAmount, formatTimeInterval, formatExactNumber } from '../utils/formatters';

interface TransactionDrawerProps {
  hop: TraceHopItem | null;
  nodeAddress?: string | null;
  nodeRole?: string | null;
  chain?: string;
  onClose: () => void;
}

export const TransactionDrawer: React.FC<TransactionDrawerProps> = ({
  hop,
  nodeAddress,
  nodeRole,
  chain,
  onClose,
}) => {
  if (!hop && !nodeAddress) return null;

  const effChain = chain || 'TRON';
  const explorerName = getExplorerName(effChain);

  const explorerUrl = hop
    ? buildExplorerUrl(hop.tx_hash, effChain, hop.explorer_url)
    : nodeAddress
    ? buildAddressExplorerUrl(nodeAddress, effChain)
    : '#';

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Scrim Backdrop (Level 2 Elevation) */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Slide-in Drawer Container */}
      <div className="relative w-full max-w-lg bg-white shadow-2xl border-l border-slate-200 h-full flex flex-col z-10 animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Layers className="w-5 h-5 text-indigo-600" />
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                {hop ? `TRANSACTION HOP #${hop.hop_number}` : 'GRAPH NODE INSPECTOR'}
              </h3>
              <p className="text-[11px] text-slate-500 font-sans">
                {hop ? 'On-Chain Transfer Record Detail' : 'Entity Role & Address Inspection'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {hop ? (
            <>
              {/* Transaction Hash */}
              <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 font-sans">
                  TRANSACTION HASH (TXID)
                </div>
                <div className="font-mono text-xs font-bold text-slate-900 break-all select-all">
                  {hop.tx_hash}
                </div>
              </div>

              {/* Hop Transfer Amount */}
              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="bg-white p-3 rounded border border-slate-200">
                  <div className="text-[10px] font-sans text-slate-500 font-medium">TRANSFER AMOUNT</div>
                  <div className="text-base font-bold text-indigo-700 tabular-nums" title={`${formatExactNumber(hop.amount)} ${hop.asset}`}>
                    {formatCryptoAmount(hop.amount, hop.asset || 'USDT')}
                  </div>
                </div>

                <div className="bg-white p-3 rounded border border-slate-200">
                  <div className="text-[10px] font-sans text-slate-500 font-medium">TEMPORAL DELTA (Δt)</div>
                  <div className="text-base font-bold text-slate-800 tabular-nums">
                    {hop.delta_t_seconds !== null && hop.delta_t_seconds !== undefined
                      ? formatTimeInterval(hop.delta_t_seconds)
                      : 'N/A'}
                  </div>
                </div>
              </div>

              {/* From / To Addresses */}
              <div className="space-y-3 font-mono">
                <div className="bg-white p-3 rounded border border-slate-200 space-y-1">
                  <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">FROM ADDRESS</div>
                  <div className="text-xs font-bold text-slate-800 break-all">{hop.from_address}</div>
                </div>

                <div className="flex justify-center">
                  <ArrowRight className="w-4 h-4 text-slate-400 rotate-90" />
                </div>

                <div className="bg-white p-3 rounded border border-slate-200 space-y-1">
                  <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">TO ADDRESS</div>
                  <div className="text-xs font-bold text-slate-800 break-all">{hop.to_address}</div>
                </div>
              </div>

              {/* Explorer URL Link */}
              <div className="pt-2">
                <a
                  href={explorerUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-3 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors font-mono font-semibold"
                >
                  <span>VIEW ON {explorerName.toUpperCase()} EXPLORER</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </>
          ) : nodeAddress ? (
            <>
              <div className="bg-slate-50 p-4 rounded border border-slate-200 space-y-2 font-mono">
                <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">NODE ADDRESS</div>
                <div className="text-sm font-bold text-slate-900 break-all">{nodeAddress}</div>
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="bg-white p-3 rounded border border-slate-200">
                  <div className="text-[10px] font-sans text-slate-500 font-medium">ASSIGNED ROLE</div>
                  <div className="text-xs font-bold text-indigo-700 uppercase">
                    {nodeRole ? nodeRole.replace('_', ' ') : 'INTERMEDIARY'}
                  </div>
                </div>

                <div className="bg-white p-3 rounded border border-slate-200">
                  <div className="text-[10px] font-sans text-slate-500 font-medium">NETWORK</div>
                  <div className="text-xs font-bold text-slate-800">{effChain.toUpperCase()}</div>
                </div>
              </div>

              {nodeRole === 'TRACE_ENDPOINT' && (
                <div className="bg-amber-50 border border-amber-200 rounded p-3 text-amber-900 text-xs font-sans leading-relaxed space-y-1">
                  <span className="font-bold font-mono text-[10px] uppercase tracking-wider block text-amber-800">
                    TRACE ENDPOINT NOTE
                  </span>
                  <p>
                    The trace currently ends at this wallet because no further relevant downstream transfer was discovered within the configured investigation scope.
                  </p>
                </div>
              )}

              <div className="pt-2">
                <a
                  href={explorerUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between p-3 rounded bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors font-mono font-semibold"
                >
                  <span>INSPECT WALLET ON {explorerName.toUpperCase()}</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </>
          ) : null}
        </div>


        {/* Drawer Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold rounded text-xs transition-colors"
          >
            CLOSE DRAWER
          </button>
        </div>
      </div>
    </div>
  );
};
