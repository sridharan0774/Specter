from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class RiskIndicatorItem(BaseModel):
    indicator_id: str = Field(..., description="Unique indicator code (e.g. RAPID_MOVEMENT)")
    indicator_name: str = Field(..., description="Human-readable indicator title")
    dimension: str = Field(..., description="Dimension: TEMPORAL, GRAPH_STRUCTURE, VALUE_FLOW, ENTITY_EXPOSURE, OBFUSCATION, BEHAVIOURAL")
    classification: str = Field("OBSERVED", description="Classification: OBSERVED, INFERRED, HEURISTIC")
    detection_rule: str = Field(..., description="Logic or threshold rule evaluated")
    observed_value: str = Field(..., description="Actual measured value from transaction data")
    threshold_reference: str = Field(..., description="Reference threshold parameter")
    contribution: float = Field(..., description="Numerical score contribution to dimension score")
    supporting_transactions: List[str] = Field(default_factory=list, description="Supporting transaction hashes/ids")
    supporting_paths: List[str] = Field(default_factory=list, description="Supporting path IDs")
    evidence_references: List[str] = Field(default_factory=list, description="Linked evidence IDs")


class RiskIndicatorResponse(BaseModel):
    trace_id: str
    case_id: Optional[str] = None
    starting_wallet: str
    chain: str = "TRON"
    asset: str = "USDT"
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Final Explainable Risk Score (0-100) or null if insufficient evidence")
    raw_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Unmitigated raw risk score (0-100)")
    contextual_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Contextually adjusted risk score after mitigation (0-100)")
    risk_level: Optional[str] = Field(None, description="Risk level: LOW (0-24), MODERATE (25-49), HIGH (50-74), VERY HIGH (75-100), or null")
    assessment_status: str = Field("ASSESSED", description="Assessment status: ASSESSED or INSUFFICIENT_EVIDENCE")
    calculation_version: str = Field("EGRE_V1", description="Explainable Graph Risk Engine calculation version")
    contextual_interpretation: str = Field(
        "Risk indicators represent observed transaction and graph patterns. They do not by themselves establish criminal activity, ownership, or illicit intent.",
        description="Standard investigative interpretation statement"
    )
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="Dimension-level capped score breakdown")
    indicators: List[RiskIndicatorItem] = Field(default_factory=list, description="Itemized explainable risk indicators")
    component_contributions: Dict[str, float] = Field(default_factory=dict, description="Legacy component score breakdown for backwards compatibility")
    contributing_factors: List[str] = Field(default_factory=list, description="Textual explanation of triggered risk factors")
    is_known_service_entity: bool = Field(False, description="Flag indicating if wallet is a known VASP/Exchange/Treasury")
    service_entity_context: bool = Field(False, description="Explicit context flag for service entity presence")
    false_positive_mitigations: List[str] = Field(default_factory=list, description="Safety mitigations applied to prevent false positive criminal classification")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
