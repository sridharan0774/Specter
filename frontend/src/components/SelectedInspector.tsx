import React, { useState } from 'react';
import type { TraceHopItem, GraphNodeDetail } from '../types/api';
import {
  ShieldCheck,
  Building2,
  FileCode,
  ArrowRight,
  ExternalLink,
  Copy,
  Check,
  Clock,
  Hash,
  Layers,
  Info,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { buildExplorerUrl, buildAddressExplorerUrl } from '../utils/explorer';
import { formatCurrency, formatCryptoAmount, formatTimeInterval } from '../utils/formatters';

interface SelectedInspectorProps {
  selectedNode: GraphNodeDetail | null;
  selectedHop: TraceHopItem | null;
  onClearSelection: () => void;
  onNavigateToAttribution?: () => void;
  onNavigateToEvidence?: () => void;
}

export const SelectedInspector: React.FC<SelectedInspectorProps> = ({
  selectedNode,
  selectedHop,
  onClearSelection,
  onNavigateToAttribution,
  onNavigateToEvidence,
}) => {
  const [copied, setCopied] = useState(false);

  if (!selectedNode && !selectedHop) {
    return (
      <div className="bg-slate-50 border border-dashed border-slate-300 rounded-lg p-6 text-center text-slate-500 font-sans mb-6">
        <div className="flex items-center justify-center space-x-2 text-xs font-semibold text-slate-600 mb-1">
          <Info className="w-4 h-4 text-indigo-600" />
          <span>INVESTIGATION GRAPH INSPECTOR</span>
        </div>
        <p className="text-xs text-slate-500 max-w-lg mx-auto">
          Click any wallet node or transaction edge in the Fund Flow graph above to inspect verifiable on-chain evidence, entity provenance, and transfer metrics.
        </p>
      </div>
    );
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const truncate = (addr: string) => {
    if (!addr || addr.length < 12) return addr;
    return `${addr.substring(0, 8)}...${addr.substring(addr.length - 8)}`;
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs font-sans mb-6 space-y-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded bg-indigo-50 text-indigo-700">
            {selectedHop ? <Hash className="w-4 h-4" /> : <Layers className="w-4 h-4" />}
          </div>
          <div>
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-900">
              {selectedHop
                ? `SELECTED TRANSACTION EDGE (HOP #${selectedHop.hop_number})`
                : `SELECTED GRAPH NODE: ${selectedNode?.walletStatus?.toUpperCase() || 'WALLET'}`}
            </h3>
            <p className="text-[11px] text-slate-500 font-sans">
              {selectedHop
                ? 'On-Chain Transfer Record & Timing Evidence'
                : 'Entity Classification, Provenance & Hop Position'}
            </p>
          </div>
        </div>

        <button
          onClick={onClearSelection}
          className="text-xs text-slate-400 hover:text-slate-700 underline font-sans"
        >
          Clear Selection
        </button>
      </div>

      {/* INSPECT TRANSACTION EDGE */}
      {selectedHop && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
            {/* From Address */}
            <div className="md:col-span-4 bg-slate-50 p-3 rounded border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 font-mono block mb-1">
                SOURCE (HOP #{selectedHop.hop_number - 1 >= 0 ? selectedHop.hop_number - 1 : 0})
              </span>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-slate-800" title={selectedHop.from_address}>
                  {truncate(selectedHop.from_address)}
                </span>
                <a
                  href={buildAddressExplorerUrl(selectedHop.from_address)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-indigo-600 p-1"
                  title="View on TronScan"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>

            {/* Arrow & Amount Flow */}
            <div className="md:col-span-4 flex flex-col items-center justify-center p-2 text-center">
              <span className="text-xs font-bold font-mono text-indigo-700 bg-indigo-50 px-3 py-1 rounded border border-indigo-200 mb-1">
                {formatCryptoAmount(selectedHop.amount, selectedHop.asset || 'USDT')}
              </span>
              <div className="flex items-center space-x-1 text-slate-400 text-xs font-mono">
                <span>Direct Transfer</span>
                <ArrowRight className="w-3.5 h-3.5 text-indigo-600" />
              </div>
            </div>

            {/* To Address */}
            <div className="md:col-span-4 bg-slate-50 p-3 rounded border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 font-mono block mb-1">
                DESTINATION (HOP #{selectedHop.hop_number})
              </span>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-slate-800" title={selectedHop.to_address}>
                  {truncate(selectedHop.to_address)}
                </span>
                <a
                  href={buildAddressExplorerUrl(selectedHop.to_address)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-400 hover:text-indigo-600 p-1"
                  title="View on TronScan"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </div>

          {/* Details Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            {/* Transaction Hash */}
            <div className="bg-slate-50 p-3 rounded border border-slate-200 font-mono">
              <span className="text-[10px] text-slate-500 font-bold block mb-1">TRANSACTION HASH</span>
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 truncate mr-2" title={selectedHop.tx_hash}>
                  {selectedHop.tx_hash}
                </span>
                <button
                  onClick={() => handleCopy(selectedHop.tx_hash)}
                  className="text-slate-400 hover:text-slate-700 p-0.5"
                  title="Copy TXID"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Timestamp */}
            <div className="bg-slate-50 p-3 rounded border border-slate-200 font-mono">
              <span className="text-[10px] text-slate-500 font-bold block mb-1">BLOCK TIMESTAMP</span>
              <div className="flex items-center space-x-1.5 text-slate-800">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-bold">
                  {selectedHop.timestamp ? new Date(selectedHop.timestamp).toUTCString() : 'N/A'}
                </span>
              </div>
            </div>

            {/* Transfer Delta */}
            <div className="bg-slate-50 p-3 rounded border border-slate-200 font-mono">
              <span className="text-[10px] text-slate-500 font-bold block mb-1">TRANSFER INTERVAL (Δt)</span>
              <div className="text-slate-800 font-bold">
                {selectedHop.delta_t_seconds !== null && selectedHop.delta_t_seconds !== undefined && selectedHop.delta_t_seconds > 0
                  ? formatTimeInterval(selectedHop.delta_t_seconds)
                  : selectedHop.hop_number === 1
                  ? 'First hop from origin'
                  : 'Simultaneous / Direct block'}
              </div>
            </div>
          </div>

          {/* Action Link */}
          <div className="flex justify-end pt-1">
            <a
              href={buildExplorerUrl(selectedHop.tx_hash, selectedHop.asset, selectedHop.explorer_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1 text-xs text-indigo-700 hover:text-indigo-900 font-semibold"
            >
              <span>View On-Chain Transaction on TronScan</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      )}

      {/* INSPECT NODE */}
      {selectedNode && !selectedHop && (
        <div className="space-y-4">
          {/* Address & Role Banner */}
          <div className="flex flex-wrap items-center justify-between p-3.5 rounded-lg border gap-3 bg-slate-50 border-slate-200">
            <div className="flex items-center space-x-3">
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                  selectedNode.role === 'VASP_ENDPOINT'
                    ? 'bg-indigo-700 text-white shadow-xs'
                    : selectedNode.role === 'TOKEN_CONTRACT'
                    ? 'bg-slate-700 text-white'
                    : selectedNode.role === 'STARTING'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-slate-300 text-slate-700'
                }`}
              >
                {selectedNode.role === 'VASP_ENDPOINT' ? (
                  <ShieldCheck className="w-5 h-5" />
                ) : selectedNode.role === 'TOKEN_CONTRACT' ? (
                  <FileCode className="w-5 h-5" />
                ) : selectedNode.role === 'NON_VASP_ENTITY' ? (
                  <Building2 className="w-5 h-5" />
                ) : (
                  <Layers className="w-5 h-5" />
                )}
              </div>

              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-bold text-sm text-slate-900 select-all">
                    {selectedNode.address}
                  </span>
                  <button
                    onClick={() => handleCopy(selectedNode.address)}
                    className="text-slate-400 hover:text-slate-700 p-0.5"
                    title="Copy Address"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <a
                    href={buildAddressExplorerUrl(selectedNode.address)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-400 hover:text-indigo-600 p-0.5"
                    title="View on TronScan"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

                <div className="flex items-center space-x-2 mt-0.5">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                      selectedNode.role === 'VASP_ENDPOINT'
                        ? 'bg-indigo-100 text-indigo-900 border border-indigo-300'
                        : selectedNode.role === 'TOKEN_CONTRACT'
                        ? 'bg-slate-200 text-slate-800 border border-slate-300'
                        : selectedNode.role === 'NON_VASP_ENTITY'
                        ? 'bg-teal-100 text-teal-900 border border-teal-300'
                        : selectedNode.role === 'STARTING'
                        ? 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                        : 'bg-slate-200 text-slate-700 border border-slate-300'
                    }`}
                  >
                    {selectedNode.walletStatus}
                  </span>

                  <span className="text-slate-400 text-xs font-mono">•</span>
                  <span className="text-slate-600 text-xs font-mono">
                    Position: <strong>Hop #{selectedNode.hopLevel}</strong>
                  </span>
                </div>
              </div>
            </div>

            {selectedNode.role === 'VASP_ENDPOINT' && selectedNode.vaspCandidate && (
              <div className="text-right">
                <span className="text-[10px] text-slate-500 font-mono uppercase block">ATTRIBUTION SCORE</span>
                <span className="text-lg font-mono font-bold text-indigo-700">
                  {selectedNode.vaspCandidate.attribution_confidence.toFixed(0)} / 100
                </span>
                <span className="text-xs text-indigo-600 font-semibold block">
                  CONFIDENCE LEVEL: {selectedNode.vaspCandidate.confidence_band}
                </span>
              </div>
            )}
          </div>

          {/* VASP SPECIFIC FORENSIC DETAILS */}
          {selectedNode.role === 'VASP_ENDPOINT' && selectedNode.vaspCandidate && (
            <div className="space-y-3 bg-indigo-50/40 p-4 rounded-lg border border-indigo-100">
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-white p-3 rounded border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">VASP ENTITY</span>
                  <span className="font-bold text-indigo-950 font-mono text-sm">
                    {selectedNode.vaspCandidate.candidate_name}
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">ENDPOINT ROLE</span>
                  <span className="font-semibold text-slate-800 font-mono text-xs">
                    {selectedNode.vaspCandidate.entity_role || 'EXCHANGE_HOT_WALLET'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">SUPPORTING TXS</span>
                  <span className="font-bold text-slate-900 font-mono text-sm">
                    {selectedNode.vaspCandidate.deposit_tx_count || 1} Transactions
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 uppercase block mb-1">OBSERVED VOLUME</span>
                  <span className="font-bold text-indigo-700 font-mono text-sm">
                    {selectedNode.vaspCandidate.value_transferred
                      ? formatCurrency(selectedNode.vaspCandidate.value_transferred)
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Why this VASP? Explanation */}
              {selectedNode.vaspCandidate.why_this_vasp && selectedNode.vaspCandidate.why_this_vasp.length > 0 && (
                <div className="bg-white p-3.5 rounded border border-indigo-100 space-y-1.5">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-indigo-900 font-mono uppercase">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    <span>WHY THIS VASP? (AUDITED FACTUAL EVIDENCE)</span>
                  </div>
                  <ul className="space-y-1 text-xs text-slate-700">
                    {selectedNode.vaspCandidate.why_this_vasp.map((reason, idx) => (
                      <li key={idx} className="flex items-start space-x-2">
                        <span className="text-indigo-600 font-bold">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Jump Actions */}
              <div className="flex items-center justify-end space-x-3 pt-1">
                {onNavigateToAttribution && (
                  <button
                    onClick={onNavigateToAttribution}
                    className="flex items-center space-x-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                  >
                    <span>View Full VASP Attribution Card</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
                {onNavigateToEvidence && (
                  <button
                    onClick={onNavigateToEvidence}
                    className="flex items-center space-x-1 text-xs font-semibold text-indigo-700 hover:text-indigo-900"
                  >
                    <span>View Evidence Items</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TOKEN CONTRACT SPECIFIC WARNING */}
          {selectedNode.role === 'TOKEN_CONTRACT' && (
            <div className="bg-amber-50/70 p-4 rounded-lg border border-amber-200 space-y-2 text-xs">
              <div className="flex items-center space-x-2 text-amber-900 font-bold font-mono">
                <Info className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>SMART CONTRACT INFRASTRUCTURE — NOT A CUSTODIAL VASP</span>
              </div>
              <p className="text-slate-700 leading-relaxed font-sans">
                Address <strong className="font-mono text-slate-900">{selectedNode.address}</strong> is the Tether USD (USDT) TRC-20 smart contract on the TRON network.
                Smart contracts execute programmatic token transfers and do not hold custodial deposits on behalf of account holders.
                SPECTER strictly isolates contract entities from VASP attribution.
              </p>
            </div>
          )}

          {/* INTERMEDIATE OR UNKNOWN WALLET NOTICE */}
          {(selectedNode.role === 'INTERMEDIATE' || selectedNode.role === 'UNKNOWN_WALLET') && (
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-xs space-y-2">
              <div className="text-slate-700">
                <span className="font-semibold">Hop #{selectedNode.hopLevel} Entity: </span>
                {selectedNode.role === 'INTERMEDIATE'
                  ? 'Transfers funds downstream through intermediate wallets toward destination endpoints.'
                  : 'Terminal leaf of current trace depth. No further outgoing transfers were identified within the configured parameters.'}
              </div>
              <div className="flex items-center space-x-3 pt-1 text-[11px] font-mono text-slate-500">
                <span>CHAIN: TRON</span>
                <span>•</span>
                <span>ASSET: USDT</span>
                <span>•</span>
                <a
                  href={buildAddressExplorerUrl(selectedNode.address)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:underline flex items-center space-x-1"
                >
                  <span>Open Address on TronScan</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
