from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WalletBase(BaseModel):
    address: str = Field(..., description="Wallet address")
    chain: str = Field(..., description="Blockchain identifier")
    entity_label: Optional[str] = Field(None, description="Known entity label if available")
    entity_type: Optional[str] = Field(None, description="Known entity category (VASP, Mixer, Exchange, etc.)")


class WalletRead(WalletBase):
    id: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_incoming: float = 0.0
    total_outgoing: float = 0.0
    tx_count: int = 0

    model_config = ConfigDict(from_attributes=True)
