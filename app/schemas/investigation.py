from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class InvestigationState(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    INGESTING = "INGESTING"
    TRACING = "TRACING"
    GRAPH_ANALYSIS = "GRAPH_ANALYSIS"
    PATTERN_ANALYSIS = "PATTERN_ANALYSIS"
    VASP_RESOLUTION = "VASP_RESOLUTION"
    EVIDENCE_BUILDING = "EVIDENCE_BUILDING"
    REPORT_GENERATION = "REPORT_GENERATION"
    PACKAGE_GENERATION = "PACKAGE_GENERATION"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class InvestigationStartRequest(BaseModel):
    wallet: str = Field(..., description="Target blockchain wallet address to investigate")
    chain: str = Field("TRON", description="Blockchain network")
    asset: str = Field("USDT", description="Asset symbol")
    max_hops: int = Field(3, ge=1, le=10, description="Maximum hop depth for multi-hop tracing")
    min_transfer_amount: float = Field(0.0, ge=0.0, description="Minimum transfer threshold")
    investigator_id: Optional[str] = Field("INV-AUTOMATED-001", description="Investigator ID")
    description: Optional[str] = Field("Automated end-to-end Specter investigation", description="Case description")


class InvestigationJobResponse(BaseModel):
    job_id: str
    case_id: str
    target_wallet: str
    chain: str
    asset: str
    status: InvestigationState
    progress_percent: float = Field(..., ge=0.0, le=100.0)
    current_stage: str
    parameters_snapshot: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FindingSchema(BaseModel):
    finding_id: str
    case_id: str
    job_id: Optional[str] = None
    finding_type: str
    title: str
    description: str
    severity: str = Field("MODERATE", description="CRITICAL, HIGH, MODERATE, LOW, INFO")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class EvidenceGraphItemSchema(BaseModel):
    evidence_id: str
    finding_id: Optional[str] = None
    case_id: str
    evidence_type: str  # TRANSACTION_EDGE, TRACE_PATH, VASP_ATTRIBUTION, VELOCITY_ALERT, TYPOLOGY_PATTERN
    finding: str
    supporting_tx_hashes: List[str] = Field(default_factory=list)
    supporting_addresses: List[str] = Field(default_factory=list)
    supporting_path_ids: List[str] = Field(default_factory=list)
    source_id: str = "SRC_TRON_RPC"
    source_name: str = "TRON Network RPC Node"
    explorer_urls: List[str] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scoring_factors: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class InvestigationSnapshotSchema(BaseModel):
    snapshot_id: str
    job_id: str
    case_id: str
    target_wallet: str
    chain: str
    asset: str
    parameters: Dict[str, Any]
    trace_graph_snapshot: Dict[str, Any]
    engine_version: str = "1.0.0"
    scoring_model_version: str = "v1.0"
    source_intelligence_version: str = "v1.0.2026"
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class InvestigationSummarySchema(BaseModel):
    case_id: str
    job_id: str
    target_wallet: str
    chain: str
    asset: str
    investigation_status: str
    risk_score: Optional[float] = None
    raw_risk_score: Optional[float] = None
    contextual_risk_score: Optional[float] = None
    risk_level: Optional[str] = None

    is_known_service_entity: bool
    service_entity_context: bool
    contextual_interpretation: str
    total_wallets_traced: int
    total_transactions_analyzed: int
    total_paths_found: int
    vasp_resolution: Dict[str, Any] = Field(default_factory=dict)
    findings_summary: List[Dict[str, Any]] = Field(default_factory=list)
    velocity_alerts_count: int = 0
    typologies_detected_count: int = 0
    evidence_count: int = 0
    execution_duration_seconds: float = 0.0
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
