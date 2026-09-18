from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceItemBase(BaseModel):
    finding: str = Field(..., description="Summary of the investigative finding")
    supporting_tx_hashes: List[str] = Field(default_factory=list, description="On-chain tx hashes backing finding")
    supporting_addresses: List[str] = Field(default_factory=list, description="Addresses involved in finding")
    source: str = Field(..., description="Data provider/engine source")
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when evidence was fetched/derived")
    scoring_factors: Dict[str, Any] = Field(default_factory=dict, description="Analytical scoring weights and components")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for finding")
    explorer_urls: List[str] = Field(default_factory=list, description="Public block explorer verification links")


class EvidenceItemCreate(EvidenceItemBase):
    case_id: str


class EvidenceItemRead(EvidenceItemBase):
    id: int
    case_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
