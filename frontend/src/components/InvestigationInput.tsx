import React, { useState } from 'react';
import { Play, CheckCircle2, Loader2, ChevronDown, ChevronUp, Sliders, Search } from 'lucide-react';
import type { InvestigationStartRequest, InvestigationJobResponse } from '../types/api';

interface InvestigationInputProps {
  onStartInvestigation: (request: InvestigationStartRequest) => void;
  isLoading: boolean;
  jobStatus?: InvestigationJobResponse | null;
  onLoadSample: () => void;
}

const STAGES = [
  'QUEUED',
  'VALIDATING',
  'INGESTING',
  'TRACING',
  'GRAPH_ANALYSIS',
  'PATTERN_ANALYSIS',
  'VASP_RESOLUTION',
  'EVIDENCE_BUILDING',
  'REPORT_GENERATION',
  'PACKAGE_GENERATION',
  'COMPLETED',
];

export const InvestigationInput: React.FC<InvestigationInputProps> = ({
  onStartInvestigation,
  isLoading,
  jobStatus,
  onLoadSample,
}) => {
  const [wallet, setWallet] = useState('TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t');
  const [chain, setChain] = useState('TRON');
  const [asset, setAsset] = useState('USDT');
  const [maxHops, setMaxHops] = useState(3);
  const [minAmount, setMinAmount] = useState(0.0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showStageDetails, setShowStageDetails] = useState(false);
  const [description] = useState('High-Velocity Multi-Hop Fund Flow & VASP Attribution');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!wallet.trim()) return;
    onStartInvestigation({
      wallet: wallet.trim(),
      chain,
      asset,
      max_hops: maxHops,
      min_transfer_amount: minAmount,
      investigator_id: 'INV-AGENT-001',
      description,
    });
  };

  const currentStageIndex = jobStatus
    ? STAGES.indexOf(jobStatus.current_stage) !== -1
      ? STAGES.indexOf(jobStatus.current_stage)
      : jobStatus.status === 'COMPLETED'
      ? STAGES.length - 1
      : 0
    : -1;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs font-sans">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Section Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-1">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-sans">
              Forensic Workbench
            </h2>
            <p className="text-sm font-semibold text-slate-900 font-sans">
              Target Wallet Investigation
            </p>
          </div>
          <button
            type="button"
            onClick={onLoadSample}
            disabled={isLoading}
            className="text-xs text-[#2563EB] hover:text-[#1d4ed8] font-medium transition-colors disabled:opacity-50"
          >
            Load Sample Case (TRON USDT)
          </button>
        </div>

        {/* Workbench Grid: Wallet (visually dominant), Chain, Asset, Primary Button */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
          {/* Target Wallet Input - Visually Dominant */}
          <div className="md:col-span-6">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Target Wallet Address
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                placeholder="Enter TRON wallet address e.g. TR7NHqje..."
                className="w-full font-mono text-sm px-3 py-2.5 pl-9 bg-slate-50 border border-slate-300 rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#3730A3] focus:border-[#3730A3] transition-all placeholder:text-slate-400 font-medium"
                required
              />
            </div>
          </div>

          {/* Chain Select */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Chain
            </label>
            <select
              value={chain}
              onChange={(e) => setChain(e.target.value)}
              className="w-full text-xs font-medium px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#3730A3] font-sans"
            >
              <option value="TRON">TRON</option>
              <option value="ETHEREUM" disabled>ETHEREUM</option>
            </select>
          </div>

          {/* Asset Select */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Asset
            </label>
            <select
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
              className="w-full text-xs font-medium px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#3730A3] font-sans"
            >
              <option value="USDT">USDT</option>
              <option value="TRX">TRX</option>
            </select>
          </div>

          {/* Start Investigation Primary Indigo Button */}
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-[#3730A3] hover:bg-[#312E81] text-white font-semibold text-xs font-sans rounded-md transition-colors duration-150 shadow-xs disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Tracing...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Start Investigation</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Collapsible Advanced Options Toggle */}
        <div className="flex items-center justify-between text-xs pt-1">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center space-x-1.5 font-sans text-xs text-slate-600 hover:text-[#3730A3] font-medium transition-colors"
          >
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span>Advanced Parameters</span>
            {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Collapsible Advanced Options */}
        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-slate-50 border border-slate-200 rounded-md text-xs font-sans mt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Maximum Trace Hops: <span className="text-[#3730A3] font-mono font-bold">{maxHops}</span>
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={maxHops}
                onChange={(e) => setMaxHops(parseInt(e.target.value, 10))}
                className="w-full accent-[#3730A3]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Minimum Transfer Amount ($)
              </label>
              <input
                type="number"
                min="0"
                step="10"
                value={minAmount}
                onChange={(e) => setMinAmount(parseFloat(e.target.value) || 0)}
                className="w-full text-xs font-mono px-3 py-2 bg-white border border-slate-300 rounded-md text-slate-800"
              />
            </div>
          </div>
        )}
      </form>

      {/* Progress Bar & Stage Status */}
      {jobStatus && (
        <div className="mt-5 pt-4 border-t border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between text-xs font-sans">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-[#3730A3]">
                {jobStatus.status === 'COMPLETED' ? 'Investigation Complete' : 'Investigation Running'}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-slate-600">Current stage: <strong className="text-slate-900 font-mono text-xs">{jobStatus.current_stage}</strong></span>
            </div>
            <div className="flex items-center space-x-3">
              <span className="font-semibold text-slate-800 font-mono tabular-nums">
                {jobStatus.progress_percent.toFixed(0)}%
              </span>
              <button
                type="button"
                onClick={() => setShowStageDetails(!showStageDetails)}
                className="text-xs text-slate-500 hover:text-slate-800 underline font-sans"
              >
                {showStageDetails ? 'Hide details' : 'Show details'}
              </button>
            </div>
          </div>

          {/* Clean Progress Line */}
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
            <div
              className="bg-[#3730A3] h-full transition-all duration-200 ease-out rounded-full"
              style={{ width: `${jobStatus.progress_percent}%` }}
            />
          </div>

          {/* Stage Details Grid */}
          {showStageDetails && (
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-1.5 text-xs font-sans pt-2">
              {STAGES.map((stg, idx) => {
                const isDone = currentStageIndex > idx || jobStatus.status === 'COMPLETED';
                const isCurrent = currentStageIndex === idx && jobStatus.status !== 'COMPLETED';

                return (
                  <div
                    key={stg}
                    className={`flex items-center space-x-1.5 px-2 py-1 rounded border text-[11px] ${
                      isDone
                        ? 'bg-emerald-50/60 text-emerald-800 border-emerald-200'
                        : isCurrent
                        ? 'bg-indigo-50 text-[#3730A3] border-indigo-200 font-semibold'
                        : 'bg-slate-50 text-slate-400 border-slate-200'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-3 h-3 text-[#3730A3] animate-spin flex-shrink-0" />
                    ) : (
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-300 flex-shrink-0" />
                    )}
                    <span className="truncate">{stg}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

