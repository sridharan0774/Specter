import React, { useState } from 'react';
import {
  Shield,
  FileText,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Download,
  ChevronDown,
  ChevronUp,
  Building,
  Layers,
  Info,
  X,
  FileCheck,
} from 'lucide-react';

import type {
  FullInvestigationDataset,
  SahyogRequestResponse,
  SahyogValidationResult,
  EvidenceChainStep,
} from '../types/api';
import { apiService } from '../services/api';

interface SahyogActionCenterProps {
  dataset: FullInvestigationDataset;
}

export const SahyogActionCenter: React.FC<SahyogActionCenterProps> = ({ dataset }) => {
  const { summary, vasp_attribution, evidence, trace_result } = dataset;
  const caseId = summary.case_id;

  // Real attribution data extraction
  const topCandidate = vasp_attribution?.candidates?.[0];
  const likelyVasp = topCandidate?.candidate_name || summary.primary_vasp_name || 'NO HIGH-CONFIDENCE VASP IDENTIFIED';
  const associatedEndpoint = topCandidate?.endpoint_address || summary.target_wallet;
  const chain = summary.chain || 'TRON';
  const asset = summary.asset || 'USDT';
  const attributionScore = topCandidate?.attribution_confidence ?? (summary.primary_vasp_confidence || 0);
  const confidenceLevel = topCandidate?.confidence_band || (attributionScore >= 80 ? 'HIGH' : attributionScore >= 50 ? 'MODERATE' : 'LOW');
  const hopDistance = topCandidate?.endpoint_hop_distance ?? 0;
  const isTerminal = topCandidate ? (topCandidate.is_terminal_endpoint !== false) : true;
  const endpointStatus = isTerminal ? 'TERMINAL ENDPOINT' : 'INTERMEDIATE ASSOCIATION';

  // Component states
  const [activeModal, setActiveModal] = useState<'DISCLOSURE' | 'FREEZE' | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [disclosureReq, setDisclosureReq] = useState<SahyogRequestResponse | null>(null);
  const [freezeReq, setFreezeReq] = useState<SahyogRequestResponse | null>(null);
  const [validationResult, setValidationResult] = useState<SahyogValidationResult | null>(null);

  const [showEvidenceChain, setShowEvidenceChain] = useState<boolean>(false);
  const [showValidationPanel, setShowValidationPanel] = useState<boolean>(false);

  // Handlers
  const handlePrepareDisclosure = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.prepareSahyogDisclosureRequest(
        caseId,
        'INV-AUTOMATED-001',
        'Authorized Law Enforcement Transaction Disclosure Request'
      );
      setDisclosureReq(res);
      if (res.validation_result) {
        setValidationResult(res.validation_result);
      }
      setActiveModal('DISCLOSURE');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handlePrepareFreeze = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.prepareSahyogFreezeRequest(
        caseId,
        'INV-AUTOMATED-001',
        'Authorized Law Enforcement Asset Preservation / Freeze Request',
        'HIGH'
      );
      setFreezeReq(res);
      if (res.validation_result) {
        setValidationResult(res.validation_result);
      }
      setActiveModal('FREEZE');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleValidatePackage = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.validateSahyogPackage(caseId);
      setValidationResult(res);
      setShowValidationPanel(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleExportPackage = async () => {
    try {
      const pkg = await apiService.getSahyogPackage(caseId);
      const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(pkg, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', `sahyog_package_${caseId}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleDownloadRequestJson = (req: SahyogRequestResponse, filename: string) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(req.request_data, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', filename);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Build evidence chain steps
  const evidenceChainSteps: EvidenceChainStep[] = [
    {
      step_number: 1,
      element_type: 'VASP',
      label: 'Identified Virtual Asset Service Provider',
      value: likelyVasp,
      detail: `Attributed entity: ${likelyVasp}`,
    },
    {
      step_number: 2,
      element_type: 'ENDPOINT_WALLET',
      label: 'VASP-Associated Deposit / Operational Endpoint',
      value: associatedEndpoint,
      detail: `Matched address: ${associatedEndpoint}`,
    },
    {
      step_number: 3,
      element_type: 'ATTRIBUTION_SCORE',
      label: 'Evidence-Backed Attribution Score & Confidence',
      value: `${attributionScore} / 100`,
      detail: `Confidence: ${confidenceLevel} | Hop Distance: ${hopDistance}`,
    },
    {
      step_number: 4,
      element_type: 'REASONING',
      label: 'Analytical Evidence & Path Convergence',
      value: topCandidate?.matched_relevance_reasons?.[0] || 'Observable multi-hop fund flow convergence',
      detail: 'Scoring factors & retention metrics',
    },
    {
      step_number: 5,
      element_type: 'SUPPORTING_TRANSACTION',
      label: 'Observable Blockchain Transactions',
      value: topCandidate?.supporting_transactions?.[0] || trace_result?.paths?.[0]?.hops?.[0]?.tx_hash || 'N/A',
      detail: `Total supporting txs: ${topCandidate?.supporting_transactions?.length || trace_result?.total_transactions_analyzed || 0}`,
    },
    {
      step_number: 6,
      element_type: 'EXPLORER_REFERENCE',
      label: 'Blockchain Explorer Reference URL',
      value: `https://tronscan.org/#/address/${associatedEndpoint}`,
      detail: 'Verifiable on-chain link',
    },
    {
      step_number: 7,
      element_type: 'VASP_PROVENANCE',
      label: 'Intelligence Source Provenance',
      value: evidence?.[0]?.source_name || 'Verified Public Intelligence Registry',
      detail: 'Documented provenance & source quality level',
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-8">
      {/* Header & Section Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-5 mb-6 gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Shield className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-bold text-white tracking-wide">SAHYOG ACTION CENTER</h2>
            <span className="bg-blue-900/60 text-blue-300 border border-blue-700/60 text-xs font-semibold px-2.5 py-0.5 rounded-full">
              READY FOR AUTHORISED API INTEGRATION
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Prepare evidence-linked enforcement requests from the current investigation.
          </p>
        </div>

        {/* Legend / Status Badges */}
        <div className="flex items-center space-x-2 text-xs">
          <span className="px-2.5 py-1 bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 rounded font-medium">
            ✓ IMPLEMENTED
          </span>
          <span className="px-2.5 py-1 bg-blue-950/80 border border-blue-700/60 text-blue-300 rounded font-medium">
            → READY FOR INTEGRATION
          </span>
          <span className="px-2.5 py-1 bg-slate-800 border border-slate-700 text-slate-400 rounded font-medium">
            • FUTURE SCOPE
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-lg flex items-center space-x-3 text-sm">
          <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ATTRIBUTION SUMMARY CARD */}
      <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 mb-6">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center space-x-2">
          <Building className="w-4 h-4 text-blue-400" />
          <span>ATTRIBUTION SUMMARY</span>
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg">
            <span className="text-xs text-slate-400 block mb-1">Likely VASP</span>
            <span className="text-base font-bold text-white truncate block" title={likelyVasp}>
              {likelyVasp}
            </span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg">
            <span className="text-xs text-slate-400 block mb-1">Associated Endpoint</span>
            <span className="text-xs font-mono font-medium text-blue-300 truncate block" title={associatedEndpoint}>
              {associatedEndpoint}
            </span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg">
            <span className="text-xs text-slate-400 block mb-1">Chain & Asset</span>
            <span className="text-sm font-semibold text-slate-200 block">
              {chain} ({asset})
            </span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800/80 p-3.5 rounded-lg">
            <span className="text-xs text-slate-400 block mb-1">Attribution Score</span>
            <div className="flex items-baseline space-x-1">
              <span className="text-lg font-bold text-emerald-400">{attributionScore}</span>
              <span className="text-xs text-slate-400">/ 100</span>
              <span
                className={`ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  confidenceLevel === 'HIGH'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-amber-950 text-amber-300 border border-amber-800'
                }`}
              >
                {confidenceLevel}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-900">
          <div className="flex items-center space-x-2 text-xs text-slate-300">
            <span className="text-slate-400">Endpoint Status:</span>
            <span className="font-semibold text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {endpointStatus}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-slate-300">
            <span className="text-slate-400">Hop Distance:</span>
            <span className="font-semibold text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {hopDistance} Hop{hopDistance !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* ACTION BUTTONS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <button
          onClick={handlePrepareDisclosure}
          disabled={loading}
          className="flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold text-xs rounded-lg transition-colors shadow-md border border-blue-500/50"
        >
          <FileText className="w-4 h-4" />
          <span>PREPARE DISCLOSURE REQUEST</span>
        </button>

        <button
          onClick={handlePrepareFreeze}
          disabled={loading}
          className="flex items-center justify-center space-x-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs rounded-lg transition-colors shadow-md border border-indigo-500/50"
        >
          <Lock className="w-4 h-4" />
          <span>PREPARE FREEZE REQUEST</span>
        </button>

        <button
          onClick={handleValidatePackage}
          disabled={loading}
          className="flex items-center justify-center space-x-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 font-semibold text-xs rounded-lg transition-colors border border-slate-700"
        >
          <FileCheck className="w-4 h-4 text-emerald-400" />
          <span>VALIDATE SAHYOG PACKAGE</span>
        </button>

        <button
          onClick={handleExportPackage}
          disabled={loading}
          className="flex items-center justify-center space-x-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 font-semibold text-xs rounded-lg transition-colors border border-slate-700"
        >
          <Download className="w-4 h-4 text-blue-400" />
          <span>EXPORT SAHYOG PACKAGE</span>
        </button>
      </div>

      {/* DISABLED SUBMIT BUTTON WITH NOTICE */}
      <div className="flex flex-col sm:flex-row items-center justify-between bg-slate-950/60 border border-slate-800/80 rounded-lg p-3.5 mb-6">
        <div className="flex items-center space-x-2.5 text-xs text-slate-400 mb-2 sm:mb-0">
          <Info className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <span>Automatic external API transmission requires official portal authorization.</span>
        </div>
        <button
          disabled
          className="w-full sm:w-auto px-4 py-2 bg-slate-900 text-slate-500 border border-slate-800 text-xs font-semibold rounded cursor-not-allowed flex items-center justify-center space-x-2"
        >
          <Lock className="w-3.5 h-3.5 text-slate-600" />
          <span>SUBMIT TO SAHYOG (COMING WITH AUTHORISED API INTEGRATION)</span>
        </button>
      </div>

      {/* VALIDATION RESULT PANEL */}
      {showValidationPanel && validationResult && (
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between mb-4 border-b border-slate-900 pb-3">
            <div className="flex items-center space-x-2">
              {validationResult.valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-rose-400" />
              )}
              <h4 className="text-sm font-bold text-white">SAHYOG PACKAGE VALIDATION RESULT</h4>
              <span
                className={`text-xs font-extrabold px-2.5 py-0.5 rounded ${
                  validationResult.valid
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                    : 'bg-rose-950 text-rose-300 border border-rose-700'
                }`}
              >
                {validationResult.status}
              </span>
            </div>
            <button
              onClick={() => setShowValidationPanel(false)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="text-xs text-slate-300 space-y-2">
            <p className="text-slate-400">
              Checked at: <span className="text-slate-200">{validationResult.checked_at}</span>
            </p>
            <div className="mt-3">
              <span className="font-semibold text-slate-400 block mb-1">Mandatory Fields Evaluated ({validationResult.checked_fields.length}):</span>
              <div className="flex flex-wrap gap-1.5">
                {validationResult.checked_fields.map((f, i) => (
                  <span key={i} className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-300 text-[11px] rounded">
                    ✓ {f}
                  </span>
                ))}
              </div>
            </div>

            {validationResult.errors && validationResult.errors.length > 0 && (
              <div className="mt-3 p-3 bg-rose-950/40 border border-rose-900/60 rounded">
                <span className="font-semibold text-rose-400 block mb-1">Validation Errors:</span>
                <ul className="list-disc list-inside space-y-1 text-rose-300 text-xs">
                  {validationResult.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* EVIDENCE CHAIN INSPECTOR ACCORDION */}
      <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowEvidenceChain(!showEvidenceChain)}
          className="w-full flex items-center justify-between p-4 bg-slate-900/60 hover:bg-slate-900 transition-colors text-left"
        >
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-bold text-white">EVIDENCE CHAIN INSPECTOR</span>
            <span className="text-xs text-slate-400">({evidenceChainSteps.length} Traceable Elements)</span>
          </div>
          {showEvidenceChain ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showEvidenceChain && (
          <div className="p-4 border-t border-slate-800 space-y-3 bg-slate-950">
            {evidenceChainSteps.map((step) => (
              <div key={step.step_number} className="flex items-start space-x-3 p-3 bg-slate-900/80 border border-slate-800/80 rounded-lg">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-950 text-blue-400 border border-blue-800 flex items-center justify-center text-xs font-bold mt-0.5">
                  {step.step_number}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300">{step.label}</span>
                    <span className="text-[10px] font-mono bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                      {step.element_type}
                    </span>
                  </div>
                  <p className="text-sm font-mono text-blue-300 font-medium truncate mt-1">{step.value}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* STATUS FOOTER */}
      <div className="mt-6 pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-2">
        <div className="flex items-center space-x-2">
          <span className="font-semibold text-slate-300">STATUS:</span>
          <span className="font-bold text-blue-400 bg-blue-950/60 border border-blue-800 px-2 py-0.5 rounded">
            READY FOR AUTHORISED API INTEGRATION
          </span>
        </div>
        <span className="text-slate-500">SPECTER Blockchain Intelligence Platform v1.0</span>
      </div>

      {/* MODAL PREVIEW FOR DISCLOSURE OR FREEZE REQUEST */}
      {activeModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950">
              <div className="flex items-center space-x-2.5">
                {activeModal === 'DISCLOSURE' ? (
                  <FileText className="w-5 h-5 text-blue-400" />
                ) : (
                  <Lock className="w-5 h-5 text-indigo-400" />
                )}
                <div>
                  <h3 className="text-base font-bold text-white">
                    {activeModal === 'DISCLOSURE' ? 'VASP INFORMATION REQUEST' : 'ASSET PRESERVATION / FREEZE REQUEST'}
                  </h3>
                  <span className="text-xs text-rose-400 font-semibold bg-rose-950/80 border border-rose-800 px-2 py-0.5 rounded mt-1 inline-block">
                    DRAFT — REQUIRES AUTHORISED REVIEW
                  </span>
                </div>
              </div>
              <button
                onClick={() => setActiveModal(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              {activeModal === 'DISCLOSURE' && disclosureReq && (
                <>
                  <div className="grid grid-cols-2 gap-3 bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-400 block">Case ID:</span>
                      <span className="text-slate-200 font-mono font-bold">{disclosureReq.case_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Investigation ID:</span>
                      <span className="text-slate-200 font-mono">{disclosureReq.job_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Target VASP:</span>
                      <span className="text-white font-bold">{disclosureReq.attributed_vasp}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Associated Endpoint:</span>
                      <span className="text-blue-300 font-mono text-[11px] truncate block" title={disclosureReq.endpoint_address}>
                        {disclosureReq.endpoint_address}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Chain & Asset:</span>
                      <span className="text-slate-200 font-semibold">{disclosureReq.chain} ({disclosureReq.asset})</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Attribution Score:</span>
                      <span className="text-emerald-400 font-bold">{disclosureReq.attribution_score} / 100 ({disclosureReq.confidence_level})</span>
                    </div>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                    <span className="font-bold text-slate-300 block">Requested Action Description:</span>
                    <p className="text-slate-300 bg-slate-900 p-2.5 rounded border border-slate-800 leading-relaxed">
                      {disclosureReq.request_data?.requested_action?.action_description}
                    </p>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                    <span className="font-bold text-slate-300 block">Supporting Evidence Summary:</span>
                    <ul className="list-disc list-inside text-slate-400 space-y-1">
                      <li>Endpoint Status: {disclosureReq.endpoint_status} ({disclosureReq.hop_distance} Hop)</li>
                      <li>Total Supporting Transactions: {disclosureReq.request_data?.evidence?.supporting_transactions?.length || 0}</li>
                      <li>Explorer Reference: {disclosureReq.request_data?.evidence?.explorer_references?.[0] || 'N/A'}</li>
                    </ul>
                  </div>
                </>
              )}

              {activeModal === 'FREEZE' && freezeReq && (
                <>
                  <div className="grid grid-cols-2 gap-3 bg-slate-950 p-4 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-400 block">Case ID:</span>
                      <span className="text-slate-200 font-mono font-bold">{freezeReq.case_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Urgency Level:</span>
                      <span className="text-rose-400 font-bold bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800 inline-block">
                        HIGH
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Relevant VASP:</span>
                      <span className="text-white font-bold">{freezeReq.attributed_vasp}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Relevant Endpoint:</span>
                      <span className="text-blue-300 font-mono text-[11px] truncate block" title={freezeReq.endpoint_address}>
                        {freezeReq.endpoint_address}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Chain & Asset:</span>
                      <span className="text-slate-200 font-semibold">{freezeReq.chain} ({freezeReq.asset})</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Attribution Score:</span>
                      <span className="text-emerald-400 font-bold">{freezeReq.attribution_score} / 100 ({freezeReq.confidence_level})</span>
                    </div>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                    <span className="font-bold text-slate-300 block">Requested Action Description:</span>
                    <p className="text-slate-300 bg-slate-900 p-2.5 rounded border border-slate-800 leading-relaxed">
                      {freezeReq.request_data?.requested_action?.action_description}
                    </p>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                    <span className="font-bold text-slate-300 block">Supporting Evidence Summary:</span>
                    <ul className="list-disc list-inside text-slate-400 space-y-1">
                      <li>Endpoint Status: {freezeReq.endpoint_status}</li>
                      <li>Supporting Transactions Count: {freezeReq.request_data?.evidence?.supporting_transactions?.length || 0}</li>
                      <li>Provenance Source: {freezeReq.request_data?.evidence?.provenance?.[0] || 'Verified Public Intelligence Registry'}</li>
                    </ul>
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-4 border-t border-slate-800 bg-slate-950">
              <div className="text-xs text-slate-400">
                Integration Status: <span className="text-blue-400 font-semibold">READY FOR AUTHORISED API INTEGRATION</span>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    if (activeModal === 'DISCLOSURE' && disclosureReq) {
                      handleDownloadRequestJson(disclosureReq, `sahyog_disclosure_request_${caseId}.json`);
                    } else if (activeModal === 'FREEZE' && freezeReq) {
                      handleDownloadRequestJson(freezeReq, `sahyog_freeze_request_${caseId}.json`);
                    }
                  }}
                  className="flex items-center space-x-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-semibold text-xs transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export Request JSON</span>
                </button>
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-semibold text-xs transition-colors"
                >
                  Close Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
