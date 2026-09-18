from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    alert_type: str = Field(..., description="Alert classification (e.g. HIGH_VELOCITY, TYPOLOGY_PEEL_CHAIN)")
    severity: str = Field(..., description="Alert severity: LOW, MEDIUM, HIGH, CRITICAL")
    explanation: str = Field(..., description="Explainable description of the detected pattern")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative metrics supporting the alert")
    supporting_tx_hashes: List[str] = Field(default_factory=list, description="List of transaction hashes")
    supporting_wallets: List[str] = Field(default_factory=list, description="List of addresses involved")


class AlertCreate(AlertBase):
    case_id: str


class AlertRead(AlertBase):
    id: int
    case_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
