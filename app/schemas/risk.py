from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class RiskIndicatorResponse(BaseModel):
    trace_id: str
    case_id: Optional[str] = None
    starting_wallet: str
    chain: str = "TRON"
    asset: str = "USDT"
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Transaction-Flow Risk Indicator score (0-100)")
    raw_risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Unmitigated raw transaction-flow risk score (0-100)")
    contextual_risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Adjusted contextual risk score after service entity mitigation (0-100)")
    contextual_interpretation: str = Field("STANDARD_TRANSACTION_FLOW", description="Contextual interpretation statement")
    risk_level: str = Field(..., description="Risk category level: LOW (0-29), MODERATE (30-59), HIGH (60-79), CRITICAL (80-100)")
    component_contributions: Dict[str, float] = Field(default_factory=dict, description="Component score breakdown")
    contributing_factors: List[str] = Field(default_factory=list, description="Textual explanation of risk factors")
    is_known_service_entity: bool = Field(False, description="Flag indicating if wallet is a known VASP/Exchange/Treasury")
    service_entity_context: bool = Field(False, description="Explicit context flag for service entity presence")
    false_positive_mitigations: List[str] = Field(default_factory=list, description="Safety mitigations applied to prevent false positive criminal classification")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
