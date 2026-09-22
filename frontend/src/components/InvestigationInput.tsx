import React, { useState } from 'react';
import { Play, CheckCircle2, Loader2, ChevronDown, ChevronUp, Sliders, Search, AlertCircle, Info, ShieldCheck } from 'lucide-react';
import type { InvestigationStartRequest, InvestigationJobResponse } from '../types/api';

interface InvestigationInputProps {
  onStartInvestigation: (request: InvestigationStartRequest, customCaseId?: string) => void;
  isLoading: boolean;
  jobStatus?: InvestigationJobResponse | null;
  onLoadSample: () => void;
  currentCaseId?: string;
  currentChain?: string;
  currentWallet?: string;
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

const CHAIN_OPTIONS = [
  { id: 'TRON', label: 'TRON (Operational)', status: 'OPERATIONAL', isLive: true, defaultAsset: 'USDT' },
  { id: 'ETHEREUM', label: 'Ethereum (Adapter Ready / Provider Required)', status: 'ADAPTER AVAILABLE / PROVIDER REQUIRED', isLive: false, defaultAsset: 'ETH' },
  { id: 'BNB', label: 'BNB Chain (Adapter Ready / Provider Required)', status: 'ADAPTER AVAILABLE / PROVIDER REQUIRED', isLive: false, defaultAsset: 'BNB' },
  { id: 'POLYGON', label: 'Polygon (Adapter Ready / Provider Required)', status: 'ADAPTER AVAILABLE / PROVIDER REQUIRED', isLive: false, defaultAsset: 'POL' },
  { id: 'BITCOIN', label: 'Bitcoin (Operational / UTXO)', status: 'OPERATIONAL / UTXO', isLive: true, defaultAsset: 'BTC' },
  { id: 'SOLANA', label: 'Solana (Adapter Ready / Provider Required)', status: 'ADAPTER AVAILABLE / PROVIDER REQUIRED', isLive: false, defaultAsset: 'SOL' },
];

const ADDRESS_REGEXES: Record<string, RegExp> = {
  TRON: /^T[1-9A-HJ-NP-Za-km-z]{33}$/,
  ETHEREUM: /^0x[a-fA-F0-9]{40}$/,
  BNB: /^0x[a-fA-F0-9]{40}$/,
  POLYGON: /^0x[a-fA-F0-9]{40}$/,
  BITCOIN: /^(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{8,87})$/,
  SOLANA: /^[1-9A-HJ-NP-Za-km-z]{32,44}$/,
};

const USDT_CONTRACT_ADDRESS = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t';

export const InvestigationInput: React.FC<InvestigationInputProps> = ({
  onStartInvestigation,
  isLoading,
  jobStatus,
  onLoadSample,
  currentCaseId,
  currentChain,
  currentWallet,
}) => {
  const [caseId, setCaseId] = useState(currentCaseId || `CASE-TRON-${new Date().getFullYear()}-001`);
  const [wallet, setWallet] = useState(currentWallet || 'TGCCfE3KJiXA2LNiKCmLZ6DT6NdL1zDWPY');
  const [chain, setChain] = useState(currentChain || 'TRON');
  const [asset, setAsset] = useState(currentChain === 'BITCOIN' ? 'BTC' : 'USDT');
  const [maxHops, setMaxHops] = useState(2);
  const [minAmount, setMinAmount] = useState(0.0);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showStageDetails, setShowStageDetails] = useState(false);
  const [description, setDescription] = useState('Multi-Hop Fund Flow & VASP Attribution Investigation');

  React.useEffect(() => {
    if (currentChain) {
      setChain(currentChain);
      const targetInfo = CHAIN_OPTIONS.find((c) => c.id === currentChain);
      if (targetInfo) {
        setAsset(targetInfo.defaultAsset);
      }
    }
  }, [currentChain]);

  React.useEffect(() => {
    if (currentWallet) {
      setWallet(currentWallet);
    }
  }, [currentWallet]);

  React.useEffect(() => {
    if (currentCaseId) {
      setCaseId(currentCaseId);
    }
  }, [currentCaseId]);


  // Real-time multi-chain address validation
  const trimmedWallet = wallet.trim();
  const currentRegex = ADDRESS_REGEXES[chain] || ADDRESS_REGEXES.TRON;
  const isUsdtContract = chain === 'TRON' && trimmedWallet.toUpperCase() === USDT_CONTRACT_ADDRESS.toUpperCase();
  const isAddressValid = trimmedWallet.length === 0 || currentRegex.test(trimmedWallet);

  const selectedChainInfo = CHAIN_OPTIONS.find((c) => c.id === chain) || CHAIN_OPTIONS[0];

  const handleChainChange = (newChain: string) => {
    setChain(newChain);
    const targetInfo = CHAIN_OPTIONS.find((c) => c.id === newChain);
    if (targetInfo) {
      setAsset(targetInfo.defaultAsset);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!trimmedWallet || !isAddressValid) return;
    onStartInvestigation(
      {
        wallet: trimmedWallet,
        chain,
        asset,
        max_hops: maxHops,
        min_transfer_amount: minAmount,
        investigator_id: 'INV-OFFICER-001',
        description,
      },
      caseId.trim() || undefined
    );
  };

  const handleSampleClick = () => {
    setChain('TRON');
    setAsset('USDT');
    setWallet('TGCCfE3KJiXA2LNiKCmLZ6DT6NdL1zDWPY');
    setCaseId('case-tron-usdt-9942');
    setMaxHops(2);
    onLoadSample();
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
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
              INVESTIGATION WORKBENCH
            </h2>
            <p className="text-sm font-semibold text-slate-900 font-sans">
              Multi-Chain Case Setup & Target Wallet Parameters
            </p>
          </div>
          <button
            type="button"
            onClick={handleSampleClick}
            disabled={isLoading}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold transition-colors disabled:opacity-50 flex items-center space-x-1"
          >
            <span>Load Benchmark Case (TGCC...DWPY → Bybit)</span>
          </button>
        </div>

        {/* Chain Operational Status Banner */}
        <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded border-l-4 border-l-indigo-600 p-2.5 text-xs">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-indigo-600" />
            <span className="font-semibold text-slate-700">Selected Chain: {selectedChainInfo.id}</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-slate-500">Status:</span>
            <span
              className={`font-mono font-bold text-[11px] px-2 py-0.5 rounded ${
                selectedChainInfo.isLive
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-amber-100 text-amber-800 border border-amber-300'
              }`}
            >
              {selectedChainInfo.status}
            </span>
          </div>
        </div>

        {/* Form Inputs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
          {/* Case Identifier */}
          <div className="md:col-span-3">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Case ID / Identifier
            </label>
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="e.g. CASE-2026-001"
              className="w-full font-mono text-xs px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 font-medium"
              required
            />
          </div>

          {/* Target Wallet Input */}
          <div className="md:col-span-5">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-semibold text-slate-700 font-sans">
                Starting Wallet Address
              </label>
              <span className="text-[10px] text-slate-500 font-mono">
                {chain} Format
              </span>
            </div>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                placeholder={`Enter target ${chain} wallet address...`}
                className={`w-full font-mono text-sm px-3 py-2.5 pl-9 bg-slate-50 border rounded-md text-slate-900 focus:outline-none focus:ring-2 transition-all font-medium ${
                  !isAddressValid
                    ? 'border-red-400 focus:ring-red-500 bg-red-50/20'
                    : isUsdtContract
                    ? 'border-amber-400 focus:ring-amber-500'
                    : 'border-slate-300 focus:ring-indigo-600 focus:border-indigo-600'
                }`}
                required
              />
            </div>
          </div>

          {/* Chain Select */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Blockchain Network
            </label>
            <select
              value={chain}
              onChange={(e) => handleChainChange(e.target.value)}
              className="w-full text-xs font-medium px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-sans"
            >
              {CHAIN_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Asset Select */}
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 font-sans mb-1">
              Asset Filter
            </label>
            <input
              type="text"
              value={asset}
              onChange={(e) => setAsset(e.target.value.toUpperCase())}
              placeholder="e.g. USDT"
              className="w-full text-xs font-mono font-medium px-3 py-2.5 bg-slate-50 border border-slate-300 rounded-md text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-600 font-sans uppercase"
              required
            />
          </div>
        </div>

        {/* Validation Messages */}
        {trimmedWallet && !isAddressValid && (
          <div className="flex items-center space-x-1.5 text-xs text-red-600 bg-red-50 p-2.5 rounded border border-red-200">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Invalid {chain} address format. Please check address characters and length for {chain}.</span>
          </div>
        )}

        {isUsdtContract && (
          <div className="flex items-start space-x-1.5 text-xs text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Notice: USDT TRC-20 Token Contract Address</span>
              <p className="text-[11px] text-amber-700 mt-0.5">
                {USDT_CONTRACT_ADDRESS} is the smart contract managing Tether USD tokens.
                SPECTER classifies token contracts as infrastructure and excludes them from VASP attribution.
              </p>
            </div>
          </div>
        )}

        {/* Action Row: Primary Start Button & Advanced Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center space-x-1.5 font-sans text-xs text-slate-600 hover:text-indigo-600 font-medium transition-colors"
          >
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span>Trace Depth & Thresholds</span>
            {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          <button
            type="submit"
            disabled={isLoading || !isAddressValid || !trimmedWallet}
            className="flex items-center justify-center space-x-2 py-2.5 px-6 bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs font-sans rounded-md transition-colors shadow-xs disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Running Multi-Chain Investigation...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start Investigation ({chain})</span>
              </>
            )}
          </button>
        </div>

        {/* Collapsible Advanced Options */}
        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 border border-slate-200 rounded-md text-xs font-sans mt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Maximum Trace Depth: <span className="text-indigo-700 font-mono font-bold">{maxHops} Hops</span>
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={maxHops}
                onChange={(e) => setMaxHops(parseInt(e.target.value, 10))}
                className="w-full accent-indigo-700 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                <span>1 hop</span>
                <span>2 hops</span>
                <span>3 hops</span>
                <span>4 hops</span>
                <span>5 hops</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Minimum Transfer Threshold ($)
              </label>
              <input
                type="number"
                min="0"
                step="10"
                value={minAmount}
                onChange={(e) => setMinAmount(parseFloat(e.target.value) || 0)}
                className="w-full text-xs font-mono px-3 py-2 bg-white border border-slate-300 rounded-md text-slate-800"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">0 = trace all transfers</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Investigation Description / Note
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full text-xs font-sans px-3 py-2 bg-white border border-slate-300 rounded-md text-slate-800"
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
              <span className="font-semibold text-indigo-700">
                {jobStatus.status === 'COMPLETED' ? 'Investigation Complete' : 'Investigation Running'}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-slate-600">
                Stage: <strong className="text-slate-900 font-mono text-xs">{jobStatus.current_stage}</strong>
              </span>
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
                {showStageDetails ? 'Hide stages' : 'Show stages'}
              </button>
            </div>
          </div>

          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200">
            <div
              className="bg-indigo-700 h-full transition-all duration-200 ease-out rounded-full"
              style={{ width: `${jobStatus.progress_percent}%` }}
            />
          </div>

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
                        ? 'bg-indigo-50 text-indigo-700 border-indigo-200 font-semibold'
                        : 'bg-slate-50 text-slate-400 border-slate-200'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-3 h-3 text-indigo-700 animate-spin flex-shrink-0" />
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
