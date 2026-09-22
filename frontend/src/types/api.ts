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

export type GraphNodeRole =
  | 'STARTING'
  | 'INTERMEDIATE'
  | 'VASP_ENDPOINT'
  | 'NON_VASP_ENTITY'
  | 'TOKEN_CONTRACT'
  | 'UNKNOWN_WALLET';

export interface GraphNodeDetail {
  address: string;
  role: GraphNodeRole;
  label: string;
  hopLevel: number;
  entityLabel?: string;
  entityRole?: string;
  walletStatus: string;
  isTerminal?: boolean;
  vaspCandidate?: VASPAttributionCandidate;
}

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
  entity_role?: string;
  endpoint_address: string;
  chain?: string;
  attribution_type: string;
  match_position?: string;
  is_terminal_endpoint?: boolean;
  confidence_band: string;
  attribution_confidence: number;
  source_confidence: number;
  endpoint_hop_distance: number;
  deposit_tx_count?: number;
  value_transferred?: number;
  value_retention_percent?: number;
  temporal_proximity_seconds?: number;
  path_convergence_count?: number;
  matched_relevance_reasons?: string[];
  evidence_summary?: string | string[];
  why_this_vasp?: string[];
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
  target_wallet?: string;
  chain: string;
  asset?: string;
  status?: string;
  resolution_status: string;
  explanation?: string;
  summary_statement?: string;
  has_high_confidence_match: boolean;
  wallets_traced_count?: number;
  transactions_traced_count?: number;
  candidates_considered_count?: number;
  known_endpoint_matches?: string[];
  negative_reason?: string;
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
  initial_transfer_amount?: number;
  downstream_activity_amount?: number;
  duration_seconds: number;
  minimum_delta_t?: number | null;
  average_delta_t?: number | null;
  maximum_delta_t?: number | null;
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
  evidence_chain?: EvidenceChainStep[];
  velocity_analysis: Record<string, any>;
  typology_analysis: Record<string, any>;
  fund_tracing_graph: Record<string, any>;
  requested_action?: Record<string, any>;
}

export interface EvidenceChainStep {
  step_number: number;
  element_type: string;
  label: string;
  value: string;
  detail: string;
}

export interface SahyogValidationResult {
  valid: boolean;
  status: 'PACKAGE VALID' | 'PACKAGE INVALID' | string;
  checked_at: string;
  checked_fields: string[];
  errors: string[];
}

export interface SahyogRequestResponse {
  request_id: string;
  case_id: string;
  job_id?: string;
  request_type: 'DISCLOSURE_REQUEST' | 'ASSET_PRESERVATION_OR_FREEZE_REQUEST' | string;
  status: 'DRAFT_REQUIRES_AUTHORISED_REVIEW' | string;
  package_version: string;
  integration_status: string;
  target_wallet: string;
  chain: string;
  asset: string;
  attributed_vasp?: string;
  endpoint_address?: string;
  attribution_score: number;
  confidence_level: string;
  hop_distance: number;
  endpoint_status: string;
  validation_result?: SahyogValidationResult;
  request_data: Record<string, any>;
  evidence_chain?: EvidenceChainStep[];
  evidence_snapshot_reference?: string;
  exported_path?: string;
  investigator_id: string;
  created_at: string;
}

export interface SahyogStatusContractResponse {
  integration_status: string;
  generator_engine: string;
  contract_notice: string;
  implemented_features: string[];
  ready_for_integration_features: string[];
  future_scope_features: string[];
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

export interface EntityIntelligenceResponse {
  address: string;
  chain: string;
  entity_name: string;
  entity_role: 'VASP' | 'DEPOSIT_WALLET' | 'HOT_WALLET' | 'OPERATIONAL_WALLET' | 'CONSOLIDATION_WALLET' | 'TOKEN_ISSUER' | 'TOKEN_CONTRACT' | 'INFRASTRUCTURE' | 'MIXER' | 'BRIDGE' | 'DEX' | 'CROSS_CHAIN_SERVICE' | 'UNKNOWN' | string;
  entity_type: string;
  label_type: string;
  cluster_id?: string;
  verification_status: 'VERIFIED' | 'ANALYTICAL' | 'UNVERIFIED' | 'UNKNOWN' | string;
  confidence: number;
  source_type: string;
  source_name: string;
  source_url?: string;
  notes?: string;
  is_attributable_vasp: boolean;
  evidence_summary: string[];
}

export interface VASPClusterResponse {
  cluster_id: string;
  vasp_name: string;
  chain: string;
  cluster_type: string;
  primary_wallet?: string;
  member_wallets: Array<{
    address: string;
    entity_role: string;
    label_type: string;
    source?: string;
  }>;
  provenance: string;
  source_quality_level: number;
  notes?: string;
}

export interface CrossChainRelationshipItem {
  relationship_id: string;
  case_id?: string;
  source_chain: string;
  source_address: string;
  source_tx_hash: string;
  service_entity: string;
  bridge_name?: string;
  destination_chain: string;
  destination_address: string;
  destination_tx_hash?: string;
  relationship_type: 'BRIDGE_TRANSFER' | 'CROSS_CHAIN_SWAP' | 'SERVICE_TRANSFER' | 'UNKNOWN' | string;
  verification_status: 'VERIFIED' | 'ANALYTICAL' | 'UNVERIFIED' | 'UNKNOWN' | string;
  confidence: number;
  evidence_summary: string[];
  provenance: string;
}

export interface PatternObservationItem {
  observation_id: string;
  case_id?: string;
  trace_id?: string;
  target_wallet: string;
  chain: string;
  pattern_type: string;
  verification_status: 'ANALYTICAL';
  confidence: number;
  confidence_band: string;
  indicator_values: Record<string, any>;
  supporting_transactions: string[];
  supporting_wallets: string[];
  explanation: string;
  observed_at: string;
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