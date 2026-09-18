from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    investigator_id: str = Field(..., min_length=1, max_length=100, description="Investigator username or ID")
    reported_wallet: str = Field(..., min_length=1, max_length=128, description="Target wallet address under investigation")
    chain: str = Field(..., min_length=1, max_length=32, description="Target blockchain network (e.g. TRON, ETHEREUM)")
    asset: str = Field("USDT", description="Primary asset under investigation (e.g. USDT, TRX, ETH)")
    description: Optional[str] = Field(None, description="Optional investigative notes/context")


class CaseUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated case status (e.g. ACTIVE, CLOSED, ARCHIVED)")
    description: Optional[str] = Field(None, description="Updated notes")


class CaseRead(BaseModel):
    case_id: str
    investigator_id: str
    reported_wallet: str
    chain: str
    asset: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseDetailRead(CaseRead):
    transaction_count: int = 0
    evidence_count: int = 0
    alert_count: int = 0
    vasp_candidate_count: int = 0
