import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { InvestigationInput } from './components/InvestigationInput';
import { InvestigationStatusBar } from './components/InvestigationStatusBar';
import { FundFlowGraph } from './components/FundFlowGraph';
import { SelectedInspector } from './components/SelectedInspector';
import { PathExplorer } from './components/PathExplorer';
import { VaspAttributionCard } from './components/VaspAttributionCard';
import { RiskBreakdownPanel } from './components/RiskBreakdownPanel';
import { VelocityAlertsPanel } from './components/VelocityAlertsPanel';
import { TypologyPanel } from './components/TypologyPanel';
import { EvidenceExplorer } from './components/EvidenceExplorer';
import { EvidenceDrawer } from './components/EvidenceDrawer';
import { TransactionDrawer } from './components/TransactionDrawer';
import { ReportsExportPanel } from './components/ReportsExportPanel';
import { SahyogActionCenter } from './components/SahyogActionCenter';
import { AlertTriangle, RefreshCw, Layers } from 'lucide-react';


import type {
  FullInvestigationDataset,
  InvestigationStartRequest,
  InvestigationJobResponse,
  EvidenceGraphItemSchema,
  TraceHopItem,
  GraphNodeDetail,
} from './types/api';

import { apiService } from './services/api';
import { MOCK_INVESTIGATION_DATASET, SAMPLE_CASE_ID } from './services/mockData';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('investigation');
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  const [healthStatus, setHealthStatus] = useState<string>('checking');

  const [dataset, setDataset] = useState<FullInvestigationDataset | null>(null);
  const [caseId, setCaseId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [jobStatus, setJobStatus] = useState<InvestigationJobResponse | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<InvestigationStartRequest | null>(null);

  const [selectedPathId, setSelectedPathId] = useState<string>('');
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceGraphItemSchema | null>(null);
  const [selectedHop, setSelectedHop] = useState<TraceHopItem | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeDetail | null>(null);

  const currentChain =
    dataset?.summary?.chain ||
    dataset?.trace_result?.chain ||
    jobStatus?.chain ||
    lastRequest?.chain ||
    sessionStorage.getItem('specter_active_chain') ||
    'TRON';

  const currentWallet =
    dataset?.summary?.target_wallet ||
    dataset?.trace_result?.starting_wallet ||
    jobStatus?.target_wallet ||
    lastRequest?.wallet ||
    sessionStorage.getItem('specter_active_wallet') ||
    '';

  // Restore Active Investigation State on Browser Reload
  useEffect(() => {
    const savedCaseId = sessionStorage.getItem('specter_active_case_id');
    if (savedCaseId && !dataset && isLiveMode) {
      setCaseId(savedCaseId);
      apiService
        .getFullInvestigationDataset(savedCaseId)
        .then((full) => {
          if (full && full.summary) {
            setDataset(full);
            if (full.summary.chain) sessionStorage.setItem('specter_active_chain', full.summary.chain);
            if (full.summary.target_wallet) sessionStorage.setItem('specter_active_wallet', full.summary.target_wallet);
            if (full.trace_result?.paths?.[0]?.path_id) {
              setSelectedPathId(full.trace_result.paths[0].path_id);
            }
          }
        })
        .catch((err) => {
          console.warn('Could not restore saved case dataset on reload:', err);
        });
    }
  }, []);

  // Sync Active State to Session Storage
  useEffect(() => {
    if (dataset) {
      const effChain = dataset.summary?.chain || dataset.trace_result?.chain || 'TRON';
      const effWallet = dataset.summary?.target_wallet || dataset.trace_result?.starting_wallet || '';
      const effCaseId = dataset.summary?.case_id || caseId;
      if (effChain) sessionStorage.setItem('specter_active_chain', effChain);
      if (effWallet) sessionStorage.setItem('specter_active_wallet', effWallet);
      if (effCaseId) sessionStorage.setItem('specter_active_case_id', effCaseId);
    }
  }, [dataset, caseId]);

  // Check Backend Health on Mount
  useEffect(() => {
    apiService
      .checkHealth()
      .then((res: any) => {
        if (res && (res.status === 'online' || res.status === 'ok')) {
          setHealthStatus('online');
        } else {
          setHealthStatus('degraded');
        }
      })
      .catch(() => {
        setHealthStatus('offline');
      });
  }, []);


  // Handle Mode Switch


  // Handle Starting Investigation
  const handleStartInvestigation = async (req: InvestigationStartRequest, customCaseId?: string) => {
    setIsLoading(true);
    setJobStatus(null);
    setApiError(null);
    setLastRequest(req);
    setSelectedNode(null);
    setSelectedHop(null);

    const effCaseId = customCaseId || caseId || `case-${req.wallet.substring(0, 8)}`;
    setCaseId(effCaseId);

    if (!isLiveMode) {
      // Demo Mode Execution (Simulated local fixture output)
      setJobStatus({
        job_id: 'job-demo-112',
        case_id: effCaseId,
        target_wallet: req.wallet,
        chain: req.chain || 'TRON',
        asset: req.asset || 'USDT',
        status: 'TRACING',
        current_stage: 'TRACING',
        progress_percent: 30.0,
        started_at: new Date().toISOString(),
      });

      setTimeout(() => {
        setJobStatus({
          job_id: 'job-demo-112',
          case_id: effCaseId,
          target_wallet: req.wallet,
          chain: req.chain || 'TRON',
          asset: req.asset || 'USDT',
          status: 'COMPLETED',
          current_stage: 'COMPLETED',
          progress_percent: 100.0,
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        });

        const demoData: FullInvestigationDataset = {
          ...MOCK_INVESTIGATION_DATASET,
          summary: {
            ...MOCK_INVESTIGATION_DATASET.summary,
            case_id: effCaseId,
            target_wallet: req.wallet,
          },
        };
        setDataset(demoData);
        setSelectedPathId(demoData.trace_result?.paths?.[0]?.path_id || '');
        setIsLoading(false);
      }, 1000);
      return;
    }

    // Strict Live Mode API Execution
    try {
      // 1. Create Case
      const caseRes = await apiService.createCase({
        target_wallet: req.wallet,
        chain: req.chain || 'TRON',
        asset: req.asset || 'USDT',
        investigator_id: req.investigator_id || 'INV-OFFICER-001',
        description: req.description,
      });

      const actualCaseId = caseRes.case_id || effCaseId;
      setCaseId(actualCaseId);

      // 2. Trigger Investigation Job
      const jobRes = await apiService.startInvestigation(actualCaseId, {
        wallet: req.wallet,
        chain: req.chain || 'TRON',
        asset: req.asset || 'USDT',
        max_hops: req.max_hops,
        min_transfer_amount: req.min_transfer_amount,
        investigator_id: req.investigator_id,
        description: req.description,
      });

      setJobStatus(jobRes);

      // 3. Poll until completed
      const finalJob = await apiService.pollJobUntilComplete(actualCaseId, (update: InvestigationJobResponse) => {
        setJobStatus(update);
      });

      if (finalJob.status === 'COMPLETED') {
        // Fetch full consolidated dataset from backend
        const full = await apiService.getFullInvestigationDataset(actualCaseId);
        setDataset(full);
        if (full.trace_result?.paths?.[0]?.path_id) {
          setSelectedPathId(full.trace_result.paths[0].path_id);
        }
      } else if (finalJob.status === 'FAILED') {
        setApiError(
          `Investigation job failed at stage ${finalJob.current_stage}: ${
            finalJob.error_message || 'Blockchain provider returned insufficient data or error.'
          }`
        );
      }
    } catch (err: any) {
      console.error('Live investigation request failed:', err);
      setApiError(
        err?.message || 'LIVE BACKEND UNAVAILABLE: Failed to complete real-time investigation via backend REST API.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadSample = () => {
    setIsLiveMode(false);
    setDataset(MOCK_INVESTIGATION_DATASET);
    setCaseId(SAMPLE_CASE_ID);
    setApiError(null);
    setSelectedPathId(MOCK_INVESTIGATION_DATASET.trace_result?.paths?.[0]?.path_id || '');
    setSelectedNode(null);
    setSelectedHop(null);
    setJobStatus({
      job_id: 'job-inv-883192',
      case_id: SAMPLE_CASE_ID,
      target_wallet: MOCK_INVESTIGATION_DATASET.summary.target_wallet,
      chain: 'TRON',
      asset: 'USDT',
      status: 'COMPLETED',
      current_stage: 'COMPLETED',
      progress_percent: 100.0,
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased">
     <Navbar
  activeTab={activeTab}
  setActiveTab={setActiveTab}
  caseId={caseId}
  isLiveMode={isLiveMode}
  healthStatus={healthStatus}
/>

      {/* Mode Status Sub-Header */}
      <div
        className={`px-6 py-2 border-b text-xs font-mono flex items-center justify-between transition-colors ${
          isLiveMode
            ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
            : 'bg-amber-50 text-amber-900 border-amber-200'
        }`}
      >
        <div className="max-w-[1440px] w-full mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isLiveMode ? 'bg-emerald-600 animate-pulse' : 'bg-amber-600'}`} />
            <span className="font-bold uppercase tracking-wider">
              {isLiveMode ? 'LIVE BLOCKCHAIN DATA MODE' : 'BENCHMARK CASE / DEMO MODE'}
            </span>
            <span className="text-[11px] opacity-80">
              — {isLiveMode ? 'Real-time REST queries against TRON Mainnet' : 'Verified SIH forensic ground-truth case'}
            </span>
          </div>

          <div className="text-[11px]">
            {isLiveMode ? (
              <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded border border-emerald-300 font-semibold">
                STRICT LIVE MODE (NO FABRICATED DATA)
              </span>
            ) : (
              <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300 font-semibold">
                SIH BENCHMARK CASE
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Workspace Container */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-6 py-8">
        {/* Backend Failure Alert Banner */}
        {apiError && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 text-red-900 space-y-3">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-red-800">
                  INVESTIGATION ALERT / BACKEND NOTICE
                </h3>
                <p className="text-xs text-red-700 font-sans">{apiError}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 pt-1 border-t border-red-200 font-mono text-xs">
              {lastRequest && (
                <button
                  onClick={() => handleStartInvestigation(lastRequest, caseId)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>RETRY INVESTIGATION</span>
                </button>
              )}
              <button
                onClick={() => handleLoadSample()}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded transition-colors"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>LOAD BENCHMARK CASE</span>
              </button>
            </div>
          </div>
        )}

        {/* WORKSPACE TAB 1: CENTRAL INVESTIGATION WORKSPACE */}
        {activeTab === 'investigation' && (
          <div className="space-y-6">
            {/* STEP 1: Case Setup & Parameters Input */}
            <InvestigationInput
              onStartInvestigation={handleStartInvestigation}
              isLoading={isLoading}
              jobStatus={jobStatus}
              onLoadSample={handleLoadSample}
              currentCaseId={caseId}
              currentChain={currentChain}
              currentWallet={currentWallet}
            />

            {/* STEP 2: Compact Investigation Summary Status Bar */}
            <InvestigationStatusBar
              summary={dataset?.summary}
              traceData={dataset?.trace_result}
              vaspData={dataset?.vasp_attribution}
              caseId={caseId || jobStatus?.case_id}
              chain={currentChain}
              maxHops={lastRequest?.max_hops || 2}
              status={jobStatus?.status || (dataset ? 'COMPLETED' : 'READY')}
            />

            {/* STEP 3: Fund Flow Graph — The Central Workspace */}
            <FundFlowGraph
              traceData={dataset?.trace_result}
              vaspData={dataset?.vasp_attribution}
              selectedPathId={selectedPathId}
              onSelectPath={setSelectedPathId}
              onNodeClick={(_addr, _role, detail) => {
                setSelectedNode(detail);
                setSelectedHop(null);
              }}
              onEdgeClick={(hop) => {
                setSelectedHop(hop);
                setSelectedNode(null);
              }}
            />

            {/* STEP 4: Selected Node / Transaction Forensic Inspector */}
            <SelectedInspector
              selectedNode={selectedNode}
              selectedHop={selectedHop}
              chain={currentChain}
              onClearSelection={() => {
                setSelectedNode(null);
                setSelectedHop(null);
              }}
              onNavigateToAttribution={() => {
                const el = document.getElementById('section-vasp-attribution');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              onNavigateToEvidence={() => {
                const el = document.getElementById('section-forensic-evidence');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
            />


            {/* STEP 5: VASP Attribution Resolution Section */}
            {dataset?.vasp_attribution && (
              <div id="section-vasp-attribution" className="space-y-3 pt-2">
                <div className="border-b border-slate-200 pb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                    VASP ATTRIBUTION & CUSTODIAL ENDPOINT RESOLUTION
                  </h3>
                  <p className="text-xs text-slate-500 font-sans">
                    Probabilistic, source-backed custodial service attribution with confidence breakdown and audited factual justification.
                  </p>
                </div>
                <VaspAttributionCard
                  vaspData={dataset.vasp_attribution}
                  onSelectNode={(addr) => {
                    const cand = dataset.vasp_attribution.candidates?.find(
                      (c) => c.endpoint_address.toUpperCase() === addr.toUpperCase()
                    );
                    setSelectedNode({
                      address: addr,
                      role: 'VASP_ENDPOINT',
                      label: `${addr.substring(0, 4)}...${addr.substring(addr.length - 4)}`,
                      hopLevel: cand?.endpoint_hop_distance || 1,
                      entityLabel: cand?.candidate_name,
                      entityRole: cand?.entity_role,
                      walletStatus: 'Verified VASP Endpoint',
                      isTerminal: true,
                      vaspCandidate: cand,
                    });
                    setSelectedHop(null);
                  }}
                />
              </div>
            )}

            {/* STEP 6: Forensic Evidence Ledger Section */}
            {dataset?.evidence && dataset.evidence.length > 0 && (
              <div id="section-forensic-evidence" className="space-y-3 pt-2">
                <div className="border-b border-slate-200 pb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                    FORENSIC EVIDENCE LEDGER
                  </h3>
                  <p className="text-xs text-slate-500 font-sans">
                    Verifiable on-chain transfer hashes, entity intelligence provenance, and derived analysis records.
                  </p>
                </div>
                <EvidenceExplorer
                  evidenceList={dataset.evidence}
                  onSelectEvidence={(item) => setSelectedEvidence(item)}
                />
              </div>
            )}

            {/* STEP 7: SAHYOG Action Center & Legal Enforcement Section */}
            {dataset && (
              <div id="section-sahyog-action-center" className="pt-2">
                <SahyogActionCenter dataset={dataset} />
              </div>
            )}

            {/* STEP 8: Reports & Export Package Section */}
            {dataset && (
              <div id="section-reports-export" className="space-y-3 pt-2">
                <div className="border-b border-slate-200 pb-2">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                    INVESTIGATION EXPORT & REPORT GENERATION
                  </h3>
                  <p className="text-xs text-slate-500 font-sans">
                    Generate audit-ready PDF intelligence report, CSV forensic datasets, and SAHYOG-ready structured package.
                  </p>
                </div>
                <ReportsExportPanel caseId={caseId} isLiveMode={isLiveMode} />
              </div>
            )}

          </div>
        )}

        {/* WORKSPACE TAB 2: FUND FLOW GRAPH ONLY */}
        {activeTab === 'fundflow' && (
          <div className="space-y-6">
            <InvestigationStatusBar
              summary={dataset?.summary}
              traceData={dataset?.trace_result}
              vaspData={dataset?.vasp_attribution}
              caseId={caseId || jobStatus?.case_id}
              maxHops={lastRequest?.max_hops || 2}
              status={jobStatus?.status || (dataset ? 'COMPLETED' : 'READY')}
            />

            <FundFlowGraph
              traceData={dataset?.trace_result}
              vaspData={dataset?.vasp_attribution}
              selectedPathId={selectedPathId}
              onSelectPath={setSelectedPathId}
              onNodeClick={(_addr, _role, detail) => {
                setSelectedNode(detail);
                setSelectedHop(null);
              }}
              onEdgeClick={(hop) => {
                setSelectedHop(hop);
                setSelectedNode(null);
              }}
            />

            <SelectedInspector
              selectedNode={selectedNode}
              selectedHop={selectedHop}
              onClearSelection={() => {
                setSelectedNode(null);
                setSelectedHop(null);
              }}
            />

            <PathExplorer
              paths={dataset?.trace_result?.paths || []}
              selectedPathId={selectedPathId}
              onSelectPath={setSelectedPathId}
            />
          </div>
        )}

        {/* WORKSPACE TAB 3: INTELLIGENCE & PATTERN ANALYTICS */}
        {activeTab === 'intelligence' && dataset && (
          <div className="space-y-6">
            <div className="border-b border-slate-200 pb-3 mb-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono">
                BLOCKCHAIN INTELLIGENCE & PATTERN ANALYTICS
              </h2>
              <p className="text-xs text-slate-500 font-sans mt-0.5">
                Plain-English investigator findings explaining who is likely involved, what looks suspicious, and why it looks suspicious.
              </p>
            </div>

            {/* Section A: WHO IS LIKELY INVOLVED? */}
            <VaspAttributionCard
              vaspData={dataset.vasp_attribution}
              onSelectNode={(addr) => {
                const cand = dataset.vasp_attribution?.candidates?.find(
                  (c) => c.endpoint_address.toUpperCase() === addr.toUpperCase()
                );
                setSelectedNode({
                  address: addr,
                  role: 'VASP_ENDPOINT',
                  label: `${addr.substring(0, 4)}...${addr.substring(addr.length - 4)}`,
                  hopLevel: cand?.endpoint_hop_distance || 1,
                  entityLabel: cand?.candidate_name,
                  entityRole: cand?.entity_role,
                  walletStatus: 'Verified VASP Endpoint',
                  isTerminal: true,
                  vaspCandidate: cand,
                });
                setSelectedHop(null);
                setActiveTab('investigation');
              }}
            />

            {/* Section B: WHAT LOOKS SUSPICIOUS? */}
            <VelocityAlertsPanel velocityData={dataset.velocity_analysis} />
            <TypologyPanel typologyData={dataset.typology_analysis} />

            {/* Section C: WHY DOES IT LOOK SUSPICIOUS? */}
            <RiskBreakdownPanel riskData={dataset.risk_indicator} />
          </div>
        )}

        {/* WORKSPACE TAB 4: FORENSIC EVIDENCE */}
        {activeTab === 'evidence' && dataset && (
          <EvidenceExplorer
            evidenceList={dataset.evidence || []}
            onSelectEvidence={(item) => setSelectedEvidence(item)}
          />
        )}

        {/* WORKSPACE TAB 5: REPORTS & EXPORTS */}
        {activeTab === 'reports' && (
          <ReportsExportPanel caseId={caseId} isLiveMode={isLiveMode} />
        )}
      </main>

      {/* Interactive Drawers */}
      <EvidenceDrawer item={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      <TransactionDrawer
        hop={selectedHop}
        nodeAddress={selectedNode?.address}
        nodeRole={selectedNode?.role}
        chain={currentChain}
        onClose={() => {
          setSelectedHop(null);
          setSelectedNode(null);
        }}
      />


      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500 font-mono">
        SPECTER HIGH-VELOCITY BLOCKCHAIN INTELLIGENCE PLATFORM • CONFIDENTIAL FORENSIC WORKSTATION
      </footer>
    </div>
  );
}

export default App;
