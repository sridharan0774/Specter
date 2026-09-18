from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


class VASPRecordBase(BaseModel):
    address: str = Field(..., description="Entity on-chain wallet or deposit address")
    chain: str = Field(..., description="Blockchain identifier")
    entity_name: str = Field(..., description="Name of entity/VASP (e.g. Binance, OKX, Huobi)")
    entity_type: str = Field(..., description="Entity category: VASP, exchange, custodial wallet, deposit wallet, hot wallet, mixer, bridge, DeFi service")
    label_type: str = Field(..., description="Label category (e.g. hot_wallet, deposit_address, cold_wallet)")
    source: str = Field(..., description="Intelligence provider/source name")
    source_url: Optional[str] = Field(None, description="Reference URL for intelligence provenance")
    source_reference: Optional[str] = Field(None, description="Dataset or advisory reference identifier")
    source_quality_level: int = Field(3, ge=1, le=5, description="Source quality level: 1 (Official) to 5 (Unverified)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of intelligence label")
    verified_at: Optional[datetime] = Field(None, description="Timestamp of label verification")
    notes: Optional[str] = Field(None, description="Additional context or notes")


class VASPRecordCreate(VASPRecordBase):
    pass


class VASPRecordRead(VASPRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VASPAttributionCandidate(BaseModel):
    rank: int = Field(..., description="Rank of candidate (1 = strongest)")
    candidate_name: str = Field(..., description="Name of candidate VASP or entity")
    endpoint_address: str = Field(..., description="Matching endpoint or intermediate wallet address")
    chain: str = Field("TRON", description="Blockchain network")
    endpoint_hop_distance: int = Field(..., description="Hop distance from suspicious starting wallet")
    attribution_type: str = Field(..., description="Attribution classification (e.g. KNOWN_DEPOSIT_ENDPOINT, KNOWN_HOT_WALLET)")
    source_confidence: float = Field(..., ge=0.0, le=1.0, description="External intelligence label confidence (0.0 - 1.0)")
    attribution_confidence: float = Field(..., ge=0.0, le=100.0, description="Overall VASP Attribution Confidence Score (0 - 100)")
    confidence_band: str = Field(..., description="Analytical confidence level: HIGH (80-100), MODERATE (60-79), LOW (40-59), INSUFFICIENT (<40)")
    score_components: Dict[str, float] = Field(default_factory=dict, description="Component score breakdown")
    evidence_summary: List[str] = Field(default_factory=list, description="Human & machine readable evidence statements")
    supporting_transactions: List[str] = Field(default_factory=list, description="Hashes of transactions connecting suspicious wallet to candidate")
    supporting_wallets: List[str] = Field(default_factory=list, description="Intermediary wallet addresses involved in path")
    path_sequence: List[str] = Field(default_factory=list, description="Ordered list of addresses from source to candidate endpoint")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Intelligence source provenance details")
    matched_relevance_reasons: List[str] = Field(default_factory=list, description="Checkmarked reasons for VASP attribution match")

    model_config = ConfigDict(from_attributes=True)


class VASPAttributionResponse(BaseModel):
    attribution_id: str = Field(..., description="Unique ID of attribution evaluation run")
    trace_id: str = Field(..., description="Associated multi-hop trace ID")
    case_id: Optional[str] = Field(None, description="Associated investigation case ID")
    starting_wallet: str = Field(..., description="Starting suspicious wallet address")
    chain: str = Field("TRON", description="Blockchain network")
    status: str = Field(..., description="Attribution status: RESOLVED or NO_HIGH_CONFIDENCE_VASP_IDENTIFIED")
    resolution_status: str = Field("", description="Resolution status string for frontend compatibility")
    has_high_confidence_match: bool = Field(False, description="Whether high confidence VASP match was resolved")
    explanation: str = Field(..., description="High-level analytical summary explanation")
    scoring_model_version: str = Field("vasp-score-v1", description="Model version for reproducibility")
    evaluated_at: datetime = Field(..., description="Timestamp of attribution evaluation")
    candidates: List[VASPAttributionCandidate] = Field(default_factory=list, description="Ranked VASP candidates")

    @model_validator(mode="after")
    def populate_computed_fields(self):
        if not self.resolution_status:
            self.resolution_status = self.status
        self.has_high_confidence_match = (
            self.status == "RESOLVED" or
            (len(self.candidates) > 0 and self.candidates[0].attribution_confidence >= 40.0)
        )
        return self

    model_config = ConfigDict(from_attributes=True)


# Backwards compatibility schema
class VASPCandidateScore(BaseModel):
    candidate_vasp: str = Field(..., description="Candidate VASP name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall attribution confidence score")
    component_scores: Dict[str, float] = Field(default_factory=dict, description="Breakdown of individual scoring factors")
    supporting_evidence: List[str] = Field(default_factory=list, description="Textual evidence statements explaining the attribution")
    transaction_path: List[str] = Field(default_factory=list, description="Chain of transaction hashes linking reported wallet to VASP")
    relevant_wallets: List[str] = Field(default_factory=list, description="Intermediary and endpoint addresses involved")
    source_labels: List[Dict[str, Any]] = Field(default_factory=list, description="Known label provenance records used in scoring")


