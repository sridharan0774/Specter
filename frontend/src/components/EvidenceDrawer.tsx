import React from 'react';
import type { EvidenceGraphItemSchema } from '../types/api';
import { X, ExternalLink, Database } from 'lucide-react';

interface EvidenceDrawerProps {
  item: EvidenceGraphItemSchema | null;
  onClose: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({ item, onClose }) => {
  if (!item) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end font-sans">
      {/* Scrim Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Slide-in Drawer Container */}
      <div className="relative w-full max-w-lg bg-white shadow-xl border-l border-slate-200 h-full flex flex-col z-10 animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between font-sans">
          <div className="flex items-center space-x-2.5">
            <Database className="w-5 h-5 text-[#3730A3]" />
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 font-sans">
                EVIDENCE ITEM: <span className="font-mono text-slate-800">{item.evidence_id}</span>
              </h3>
              <p className="text-[11px] text-slate-500 font-sans mt-0.5">
                {item.source_name} ({item.source_id})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs font-sans">
          {/* Finding Statement */}
          <div className="bg-slate-50/60 p-4 rounded-md border border-slate-200 space-y-1">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-sans">
              Analytical Finding Statement
            </div>
            <p className="text-xs text-slate-800 font-sans leading-relaxed">
              {item.finding}
            </p>
          </div>

          {/* Evidence Properties Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs font-sans">
            <div className="bg-white p-3 rounded-md border border-slate-200">
              <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">TYPE</div>
              <div className="text-xs font-semibold text-slate-900 font-sans">{item.evidence_type}</div>
            </div>

            <div className="bg-white p-3 rounded-md border border-slate-200">
              <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">CONFIDENCE</div>
              <div className="text-xs font-bold text-[#3730A3] font-mono tabular-nums">
                {(item.confidence * 100).toFixed(1)} / 100.0
              </div>
            </div>

            <div className="bg-white p-3 rounded-md border border-slate-200">
              <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">CASE ID</div>
              <div className="text-xs font-bold text-slate-900 font-mono">{item.case_id}</div>
            </div>

            <div className="bg-white p-3 rounded-md border border-slate-200">
              <div className="text-[10px] font-sans text-slate-500 font-medium uppercase">TIMESTAMP</div>
              <div className="text-xs font-bold text-slate-800 font-mono tabular-nums">
                {new Date(item.retrieval_timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>

          {/* Supporting Blockchain Hashes */}
          {item.supporting_tx_hashes && item.supporting_tx_hashes.length > 0 && (
            <div className="space-y-2 font-sans">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-sans">
                SUPPORTING TRANSACTION HASHES ({item.supporting_tx_hashes.length})
              </div>
              <div className="space-y-1.5 font-mono text-[11px]">
                {item.supporting_tx_hashes.map((hash, hIdx) => (
                  <div key={hIdx} className="bg-slate-50/60 p-2.5 rounded-md border border-slate-200 text-slate-800 truncate">
                    {hash}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Supporting Addresses */}
          {item.supporting_addresses && item.supporting_addresses.length > 0 && (
            <div className="space-y-2 font-sans">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-sans">
                SUPPORTING WALLET ADDRESSES ({item.supporting_addresses.length})
              </div>
              <div className="space-y-1.5 font-mono text-[11px]">
                {item.supporting_addresses.map((addr, aIdx) => (
                  <div key={aIdx} className="bg-slate-50/60 p-2.5 rounded-md border border-slate-200 text-slate-800 truncate">
                    {addr}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Explorer Links */}
          {item.explorer_urls && item.explorer_urls.length > 0 && (
            <div className="space-y-2 pt-2 border-t border-slate-100 font-sans">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 font-sans">
                VERIFIABLE BLOCK EXPLORER LINKS
              </div>
              <div className="space-y-1.5 font-mono text-xs">
                {item.explorer_urls.map((url, uIdx) => (
                  <a
                    key={uIdx}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between p-2.5 rounded-md bg-indigo-50/60 text-[#2563EB] hover:text-[#1d4ed8] hover:bg-indigo-50 border border-indigo-100 transition-colors"
                  >
                    <span className="truncate max-w-[280px] text-slate-700">{url}</span>
                    <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="px-6 py-4 bg-slate-50/80 border-t border-slate-100 flex justify-end font-sans">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 font-semibold rounded-md text-xs transition-colors font-sans"
          >
            CLOSE EVIDENCE DRAWER
          </button>
        </div>
      </div>
    </div>
  );
};