from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TypologyResult(BaseModel):
    typology_id: str = Field(..., description="Unique typology detection ID")
    typology_name: str = Field(..., description="Typology name: FAN_OUT, FAN_IN, CONSOLIDATION, RAPID_PEEL_LIKE_MOVEMENT, REPEATED_INTERACTION, VASP_CONVERGENCE, KNOWN_SERVICE_ENTITY")
    severity: str = Field(..., description="Severity level: LOW, MODERATE, HIGH, CRITICAL")
    description: str = Field(..., description="Analytical description statement")
    trigger_conditions: List[str] = Field(default_factory=list, description="Rule conditions triggered")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative pattern metrics")
    supporting_transactions: List[str] = Field(default_factory=list, description="Supporting transaction hashes")
    supporting_wallets: List[str] = Field(default_factory=list, description="Supporting wallet addresses")
    supporting_paths: List[str] = Field(default_factory=list, description="Supporting trace path IDs or wallet sequences")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0.0 - 1.0)")
    is_known_service: bool = Field(False, description="True if pattern originates from or terminates at a known exchange/service")

    model_config = ConfigDict(from_attributes=True)


class TypologyAnalysisResponse(BaseModel):
    trace_id: str
    case_id: Optional[str] = None
    starting_wallet: str
    chain: str = "TRON"
    asset: str = "USDT"
    status: str = Field(..., description="TYPOLOGIES_DETECTED or NO_MATERIAL_TYPOLOGY_DETECTED")
    summary: str
    typologies: List[TypologyResult] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
