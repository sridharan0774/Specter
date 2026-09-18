import React, { useState } from 'react';
import type { EvidenceGraphItemSchema } from '../types/api';
import { ChevronRight, Search, ShieldCheck } from 'lucide-react';

interface EvidenceExplorerProps {
  evidenceList: EvidenceGraphItemSchema[];
  onSelectEvidence: (item: EvidenceGraphItemSchema) => void;
}

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({ evidenceList, onSelectEvidence }) => {
  const [activeCategory, setActiveCategory] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const categories = ['ALL', 'ON_CHAIN', 'ENTITY_INTELLIGENCE', 'DERIVED_ANALYSIS'];

  const filteredEvidence = evidenceList.filter((item) => {
    const matchesCat = activeCategory === 'ALL' || item.evidence_type === activeCategory;
    const matchesSearch =
      item.finding.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.source_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.evidence_id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const getCategoryColor = (type: string) => {
    switch (type) {
      case 'ON_CHAIN':
        return 'border-l-indigo-600 bg-slate-50/60';
      case 'ENTITY_INTELLIGENCE':
        return 'border-l-teal-600 bg-slate-50/60';
      case 'DERIVED_ANALYSIS':
        return 'border-l-purple-600 bg-slate-50/60';
      default:
        return 'border-l-slate-400 bg-slate-50/60';
    }
  };

  const getCategoryTickColor = (type: string) => {
    switch (type) {
      case 'ON_CHAIN':
        return 'bg-[#3730A3]';
      case 'ENTITY_INTELLIGENCE':
        return 'bg-teal-600';
      case 'DERIVED_ANALYSIS':
        return 'bg-purple-600';
      default:
        return 'bg-slate-400';
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs mb-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-4 mb-6 gap-4 font-sans">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-[#3730A3]" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-800 font-sans">
              EVIDENCE SUPPORTING THIS INVESTIGATION ({evidenceList.length})
            </h2>
          </div>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Strictly verifiable on-chain ledger records, entity intelligence matches, and derived flow analytics.
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search evidence ledger..."
            className="text-xs font-sans px-3 py-1.5 pl-8 bg-slate-50 border border-slate-300 rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#3730A3] focus:bg-white w-64 transition-all"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 font-sans">
        {/* Left Vertical Category Rail */}
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 px-3 py-1 font-sans">
            CATEGORY FILTER
          </div>
          {categories.map((cat) => {
            const count =
              cat === 'ALL'
                ? evidenceList.length
                : evidenceList.filter((e) => e.evidence_type === cat).length;
            const isSelected = activeCategory === cat;

            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`w-full flex items-center justify-between px-3.5 py-2 rounded-md text-xs font-semibold font-sans tracking-tight transition-colors text-left ${
                  isSelected
                    ? 'bg-indigo-50 text-[#3730A3] border border-indigo-200'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <span className={`w-2 h-2 rounded-full ${getCategoryTickColor(cat)}`} />
                  <span>{cat.replace('_', ' ')}</span>
                </div>
                <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[10px] font-mono tabular-nums">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Evidence List Grid */}
        <div className="lg:col-span-3 space-y-3">
          {filteredEvidence.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-md border border-slate-200 text-xs text-slate-500 font-sans">
              No evidence records found matching selected filter parameters.
            </div>
          ) : (
            filteredEvidence.map((item) => (
              <div
                key={item.evidence_id}
                onClick={() => onSelectEvidence(item)}
                className={`p-4 rounded-md border border-slate-200 border-l-2 ${getCategoryColor(
                  item.evidence_type
                )} cursor-pointer hover:border-slate-300 transition-all flex flex-col justify-between space-y-3 font-sans shadow-xs`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-xs font-sans">
                      <span className="font-mono font-bold text-slate-900">{item.evidence_id}</span>
                      <span className="text-slate-300">•</span>
                      <span className="text-slate-600 font-sans font-medium">{item.source_name}</span>
                    </div>

                    <p className="text-xs text-slate-700 font-sans leading-relaxed pt-0.5">
                      {item.finding}
                    </p>
                  </div>

                  <div className="text-right text-xs flex-shrink-0 font-sans">
                    <span className="text-slate-400 font-sans text-[10px] uppercase font-semibold">CONFIDENCE</span>
                    <div className="font-mono font-bold text-[#3730A3] tabular-nums">
                      {(item.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>

                {/* Explorer Links & Supporting References */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200/80 text-xs">
                  <div className="flex items-center space-x-2 text-slate-500 font-mono text-[11px]">
                    <span>TXS: {item.supporting_tx_hashes?.length || 0}</span>
                    <span className="text-slate-300">•</span>
                    <span>ADDRS: {item.supporting_addresses?.length || 0}</span>
                  </div>

                  <div className="flex items-center space-x-1 text-[#3730A3] font-sans font-semibold text-[11px] hover:text-[#312E81] transition-colors">
                    <span>VIEW EVIDENCE</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
