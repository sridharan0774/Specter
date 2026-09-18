export type InvestigationState =
  | 'QUEUED'
  | 'VALIDATING'
  | 'INGESTING'
  | 'TRACING'
  | 'GRAPH_ANALYSIS'
  | 'PATTERN_ANALYSIS'
  | 'VASP_RESOLUTION'
  | 'EVIDENCE_BUILDING'
  | 'REPORT_GENERATION'
  | 'PACKAGE_GENERATION'
  | 'COMPLETED'
  | 'PARTIAL'
  | 'FAILED';

export interface InvestigationStartRequest {
  wallet: string;
  chain?: string;
  asset?: string;
  max_hops?: number;
  min_transfer_amount?: number;
  investigator_id?: string;
  description?: string;
}

export interface InvestigationJobResponse {
  job_id: string;
  case_id: string;
  target_wallet: string;
  chain: string;
  asset: string;
  status: InvestigationState;
  progress_percent: number;
  current_stage: string;
  started_at: string;
  completed_at?: string;
  parameters_snapshot?: Record<string, any>;
  error_message?: string;
}

export interface FindingSchema {
  finding_id: string;
  case_id: string;
  job_id: string;
  finding_type: string;
  title: string;
  description: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'INFO';
  confidence: number;
  supporting_evidence_ids: string[];
  metadata?: Record<string, any>;
}

export interface EvidenceGraphItemSchema {
  evidence_id: string;
  finding_id?: string;
  case_id: string;
  evidence_type: 'ON_CHAIN' | 'ENTITY_INTELLIGENCE' | 'DERIVED_ANALYSIS' | string;
  finding: string;
  supporting_tx_hashes: string[];
  supporting_addresses: string[];
  supporting_path_ids: string[];
  source_id: string;
  source_name: string;
  explorer_urls: string[];
  confidence: number;
  scoring_factors: Record<string, any>;
  retrieval_timestamp: string;
}

export interface InvestigationSummarySchema {
  case_id: string;
  job_id: string;
  target_wallet: string;
  chain: string;
  asset: string;
  investigation_status: string;
  execution_duration_seconds: number;
  completed_at: string;
  total_wallets_traced: number;
  total_transactions_analyzed: number;
  total_paths_found: number;
  risk_score: number;
  raw_risk_score: number;
  contextual_risk_score: number;
  risk_level: string;
  service_entity_context: boolean;
  primary_vasp_name?: string;
  primary_vasp_confidence?: number;
  evidence_count: number;
}

export interface TraceHopItem {
  hop_number: number;
  from_address: string;
  to_address: string;
  tx_hash: string;
  asset: string;
  amount: number;
  timestamp: string;
  block_number?: number;
  delta_t_seconds: number;
  explorer_url: string;
}

export interface TracePathDetail {
  path_id: string;
  wallet_sequence: string[];
  hop_count: number;
  initial_amount: number;
  final_amount: number;
  value_retention_percent: number;
  elapsed_time_seconds: number;
  relevance_score: number;
  relevance_explanation: string[];
  cycle_detected: boolean;
  metrics: Record<string, any>;
  hops: TraceHopItem[];
}

export interface TraceResultResponse {
  trace_id: string;
  case_id?: string;
  starting_wallet: string;
  chain: string;
  asset: string;
  status: string;
  truncated: boolean;
  truncation_reason?: string;
  total_wallets_discovered: number;
  total_transactions_analyzed: number;
  total_edges_discovered: number;
  total_paths_found: number;
  processing_time_seconds: number;
  started_at: string;
  completed_at?: string;
  paths: TracePathDetail[];
}

export interface VASPAttributionCandidate {
  rank?: number;
  candidate_name: string;
  endpoint_address: string;
  chain?: string;
  attribution_type: string;
  confidence_band: string;
  attribution_confidence: number;
  source_confidence: number;
  endpoint_hop_distance: number;
  deposit_tx_count?: number;
  matched_relevance_reasons?: string[];
  evidence_summary?: string | string[];
  score_components?: Record<string, number>;
  supporting_transactions?: string[];
  supporting_wallets?: string[];
  path_sequence?: string[];
  source_metadata?: Record<string, any>;
}

export interface VASPAttributionResponse {
  attribution_id?: string;
  case_id?: string;
  trace_id: string;
  starting_wallet: string;
  chain: string;
  asset?: string;
  status?: string;
  resolution_status: string;
  explanation?: string;
  summary_statement?: string;
  has_high_confidence_match: boolean;
  candidates: VASPAttributionCandidate[];
  missing_evidence_factors?: string[];
  confidence_explanation?: string;
}

export interface VelocityAlert {
  alert_id: string;
  trace_id: string;
  case_id?: string;
  alert_type: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  velocity_score: number;
  transfer_count: number;
  total_amount: number;
  duration_seconds: number;
  minimum_delta_t: number;
  average_delta_t: number;
  maximum_delta_t: number;
  unique_recipients: number;
  downstream_hops: number;
  supporting_transactions: string[];
  supporting_wallets: string[];
  reason_codes: string[];
  score_components: Record<string, number>;
  explanation: string;
  analyzed_at: string;
}

export interface VelocityAnalysisResponse {
  trace_id: string;
  case_id?: string;
  starting_wallet: string;
  chain: string;
  asset: string;
  has_high_velocity_pattern: boolean;
  status: string;
  summary: string;
  alerts: VelocityAlert[];
  metrics: Record<string, any>;
}

export interface TypologyResult {
  typology_id: string;
  typology_name: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  description: string;
  trigger_conditions: string[];
  metrics: Record<string, any>;
  supporting_transactions: string[];
  supporting_wallets: string[];
  supporting_paths: string[];
  confidence: number;
  is_known_service: boolean;
}

export interface TypologyAnalysisResponse {
  trace_id: string;
  case_id?: string;
  starting_wallet: string;
  chain: string;
  asset: string;
  status: string;
  summary: string;
  typologies: TypologyResult[];
  analyzed_at: string;
}

export interface RiskIndicatorResponse {
  trace_id: string;
  case_id?: string;
  starting_wallet: string;
  chain: string;
  asset: string;
  risk_score: number;
  raw_risk_score: number;
  contextual_risk_score: number;
  contextual_interpretation: string;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  component_contributions: Record<string, number>;
  contributing_factors: string[];
  is_known_service_entity: boolean;
  service_entity_context: boolean;
  false_positive_mitigations: string[];
  analyzed_at: string;
}

export interface SahyogPackage {
  sahyog_metadata: {
    integration_status: string;
    generator_engine: string;
    export_timestamp: string;
    schema_version: string;
    notice: string;
  };
  case_details: {
    case_id: string;
    job_id: string;
    target_wallet: string;
    chain: string;
    asset: string;
    investigation_status: string;
    execution_duration_seconds: number;
    completed_at: string;
  };
  risk_assessment: Record<string, any>;
  vasp_attribution: Record<string, any>;
  analytical_findings: Record<string, any>[];
  evidence_ledger: Record<string, any>[];
  velocity_analysis: Record<string, any>;
  typology_analysis: Record<string, any>;
  fund_tracing_graph: Record<string, any>;
}

export interface FullInvestigationDataset {
  summary: InvestigationSummarySchema;
  risk_indicator: RiskIndicatorResponse;
  vasp_attribution: VASPAttributionResponse;
  findings: FindingSchema[];
  evidence: EvidenceGraphItemSchema[];
  velocity_analysis: VelocityAnalysisResponse;
  typology_analysis: TypologyAnalysisResponse;
  trace_result: TraceResultResponse;
}

export interface CaseRead {
  case_id: string;
  investigator_id: string;
  reported_wallet: string;
  chain: string;
  asset: string;
  status: string;
  description?: string;
  created_at: string;
  updated_at: string;
}