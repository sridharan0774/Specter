import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { InvestigationInput } from './components/InvestigationInput';
import { PrimaryResultReveal } from './components/PrimaryResultReveal';
import { SuspiciousAlertsBanner } from './components/SuspiciousAlertsBanner';
import { FundFlowGraph } from './components/FundFlowGraph';
import { PathExplorer } from './components/PathExplorer';
import { VaspAttributionCard } from './components/VaspAttributionCard';
import { RiskBreakdownPanel } from './components/RiskBreakdownPanel';
import { VelocityAlertsPanel } from './components/VelocityAlertsPanel';
import { TypologyPanel } from './components/TypologyPanel';
import { EvidenceExplorer } from './components/EvidenceExplorer';
import { EvidenceDrawer } from './components/EvidenceDrawer';
import { TransactionDrawer } from './components/TransactionDrawer';
import { ReportsExportPanel } from './components/ReportsExportPanel';
import { AlertTriangle, RefreshCw, Layers } from 'lucide-react';

import type {
  FullInvestigationDataset,
  InvestigationStartRequest,
  InvestigationJobResponse,
  EvidenceGraphItemSchema,
  TraceHopItem,
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
  const [selectedNodeAddress, setSelectedNodeAddress] = useState<string | null>(null);
  const [selectedNodeRole, setSelectedNodeRole] = useState<string | null>(null);

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
  const handleToggleMode = (live: boolean) => {
    setIsLiveMode(live);
    setApiError(null);
    if (!live) {
      // Switched to Demo Mode -> Load Fixture Data
      setDataset(MOCK_INVESTIGATION_DATASET);
      setCaseId(SAMPLE_CASE_ID);
      setSelectedPathId(MOCK_INVESTIGATION_DATASET.trace_result?.paths?.[0]?.path_id || '');
    } else {
      // Switched to Live Mode -> Clear Fixture Data if loaded
      if (dataset === MOCK_INVESTIGATION_DATASET) {
        setDataset(null);
        setCaseId('');
        setSelectedPathId('');
      }
    }
  };

  // Handle Starting Investigation
  const handleStartInvestigation = async (req: InvestigationStartRequest) => {
    setIsLoading(true);
    setJobStatus(null);
    setApiError(null);
    setLastRequest(req);

    if (!isLiveMode) {
      // Demo Mode Execution (Simulated local fixture output)
      setJobStatus({
        job_id: 'job-demo-112',
        case_id: req.wallet ? `case-${req.wallet.substring(0, 8)}` : SAMPLE_CASE_ID,
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
          case_id: req.wallet ? `case-${req.wallet.substring(0, 8)}` : SAMPLE_CASE_ID,
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
            target_wallet: req.wallet,
          },
        };
        setDataset(demoData);
        setCaseId(`case-${req.wallet.substring(0, 8)}`);
        setSelectedPathId(demoData.trace_result?.paths?.[0]?.path_id || '');
        setIsLoading(false);
      }, 1200);
      return;
    }

    // Strict Live Mode API Execution
    try {
      // 1. Create Case
      const caseRes = await apiService.createCase({
        target_wallet: req.wallet,
        chain: req.chain || 'TRON',
        asset: req.asset || 'USDT',
        investigator_id: req.investigator_id,
        description: req.description,
      });

      setCaseId(caseRes.case_id);

      // 2. Trigger Investigation Job
      const jobRes = await apiService.startInvestigation(caseRes.case_id, {
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
      const finalJob = await apiService.pollJobUntilComplete(caseRes.case_id, (update: InvestigationJobResponse) => {
        setJobStatus(update);
      });

      if (finalJob.status === 'COMPLETED') {
        // Fetch full dataset from backend
        const full = await apiService.getFullInvestigationDataset(caseRes.case_id);
        setDataset(full);
        if (full.trace_result?.paths?.[0]?.path_id) {
          setSelectedPathId(full.trace_result.paths[0].path_id);
        }
      } else if (finalJob.status === 'FAILED') {
        setApiError(`Investigation job failed on stage ${finalJob.current_stage}: ${finalJob.error_message || 'Backend processing error'}`);
      }
    } catch (err: any) {
      console.error('Live investigation request failed:', err);
      setApiError(
        err?.message || 'LIVE BACKEND UNAVAILABLE: Failed to complete real-time investigation via backend REST API.'
      );
      // STRICT REQUIREMENT: NEVER fallback to mock data on error during Live Mode
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
      {/* Header Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        caseId={caseId}
        isLiveMode={isLiveMode}
        setIsLiveMode={handleToggleMode}
        healthStatus={healthStatus}
      />

      {/* Live vs Demo Status Indicator Sub-Header */}
      <div className={`px-6 py-2 border-b text-xs font-mono flex items-center justify-between transition-colors ${
        isLiveMode
          ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
          : 'bg-amber-50 text-amber-900 border-amber-200'
      }`}>
        <div className="max-w-[1440px] w-full mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isLiveMode ? 'bg-emerald-600 animate-pulse' : 'bg-amber-600'}`} />
            <span className="font-bold uppercase tracking-wider">
              {isLiveMode ? 'LIVE BLOCKCHAIN DATA MODE' : 'DEMO / FIXTURE DATASET MODE'}
            </span>
            <span className="text-[11px] opacity-80">
              — {isLiveMode ? 'Executing direct backend REST queries against TRON mainnet' : 'Operating on static fixture dataset'}
            </span>
          </div>

          <div className="text-[11px]">
            {isLiveMode ? (
              <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded border border-emerald-300 font-semibold">
                STRICT LIVE MODE (NO MOCK FALLBACK)
              </span>
            ) : (
              <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300 font-semibold">
                DEMO BENCHMARK DATASET
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
                  LIVE BACKEND UNAVAILABLE
                </h3>
                <p className="text-xs text-red-700 font-sans">{apiError}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3 pt-1 border-t border-red-200 font-mono text-xs">
              {lastRequest && (
                <button
                  onClick={() => handleStartInvestigation(lastRequest)}
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
                <span>SWITCH TO DEMO MODE</span>
              </button>
            </div>
          </div>
        )}

        {/* Workspace Tab 1: INVESTIGATION (Main Landing Workspace) */}
        {activeTab === 'investigation' && (
          <div className="space-y-6">
            <InvestigationInput
              onStartInvestigation={handleStartInvestigation}
              isLoading={isLoading}
              jobStatus={jobStatus}
              onLoadSample={handleLoadSample}
            />

            {dataset && (
              <>
                {/* 1. Primary Conclusion & Highest-Confidence VASP Reveal */}
                <PrimaryResultReveal
                  summary={dataset.summary}
                  vaspData={dataset.vasp_attribution}
                  riskData={dataset.risk_indicator}
                  onNavigateToTab={setActiveTab}
                />

                {/* 2. Compact Suspicious Movement Alerts (Velocity & Typology) */}
                <SuspiciousAlertsBanner
                  velocityData={dataset.velocity_analysis}
                  typologyData={dataset.typology_analysis}
                  onViewTrace={() => setActiveTab('fundflow')}
                />

                {/* 3. Ranked Trace Path Cards Preview */}
                <PathExplorer
                  paths={dataset.trace_result?.paths || []}
                  selectedPathId={selectedPathId}
                  onSelectPath={setSelectedPathId}
                  onNavigateToGraph={() => setActiveTab('fundflow')}
                />

                {/* 4. Hierarchical Fund Flow Visualizer */}
                <FundFlowGraph
                  traceData={dataset.trace_result}
                  vaspData={dataset.vasp_attribution}
                  selectedPathId={selectedPathId}
                  onSelectPath={setSelectedPathId}
                  onNodeClick={(addr, role) => {
                    setSelectedNodeAddress(addr);
                    setSelectedNodeRole(role);
                    setSelectedHop(null);
                  }}
                  onEdgeClick={(hop) => {
                    setSelectedHop(hop);
                    setSelectedNodeAddress(null);
                  }}
                />
              </>
            )}
          </div>
        )}

        {/* Workspace Tab 2: FUND FLOW */}
        {activeTab === 'fundflow' && (
          <div className="space-y-6">
            <FundFlowGraph
              traceData={dataset?.trace_result}
              vaspData={dataset?.vasp_attribution}
              selectedPathId={selectedPathId}
              onSelectPath={setSelectedPathId}
              onNodeClick={(addr, role) => {
                setSelectedNodeAddress(addr);
                setSelectedNodeRole(role);
                setSelectedHop(null);
              }}
              onEdgeClick={(hop) => {
                setSelectedHop(hop);
                setSelectedNodeAddress(null);
              }}
            />

            <PathExplorer
              paths={dataset?.trace_result?.paths || []}
              selectedPathId={selectedPathId}
              onSelectPath={setSelectedPathId}
            />
          </div>
        )}

        {/* Workspace Tab 3: INTELLIGENCE */}
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
                setSelectedNodeAddress(addr);
                setSelectedNodeRole('VASP_ENDPOINT');
              }}
            />

            {/* Section B: WHAT LOOKS SUSPICIOUS? */}
            <VelocityAlertsPanel velocityData={dataset.velocity_analysis} />
            <TypologyPanel typologyData={dataset.typology_analysis} />

            {/* Section C: WHY DOES IT LOOK SUSPICIOUS? */}
            <RiskBreakdownPanel riskData={dataset.risk_indicator} />
          </div>
        )}

        {/* Workspace Tab 4: EVIDENCE */}
        {activeTab === 'evidence' && dataset && (
          <EvidenceExplorer
            evidenceList={dataset.evidence || []}
            onSelectEvidence={(item) => setSelectedEvidence(item)}
          />
        )}

        {/* Workspace Tab 5: REPORTS & EXPORTS */}
        {activeTab === 'reports' && (
          <ReportsExportPanel caseId={caseId} isLiveMode={isLiveMode} />
        )}
      </main>

      {/* Interactive Drawers */}
      <EvidenceDrawer item={selectedEvidence} onClose={() => setSelectedEvidence(null)} />

      <TransactionDrawer
        hop={selectedHop}
        nodeAddress={selectedNodeAddress}
        nodeRole={selectedNodeRole}
        onClose={() => {
          setSelectedHop(null);
          setSelectedNodeAddress(null);
          setSelectedNodeRole(null);
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
