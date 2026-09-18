from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NormalizedTransactionBase(BaseModel):
    chain: str = Field(..., description="Blockchain identifier (e.g. TRON, ETHEREUM, POLYGON, BSC)")
    tx_hash: str = Field(..., description="On-chain transaction hash")
    block_number: Optional[int] = Field(None, description="Block height in which the transaction was included (None if unavailable)")
    timestamp: datetime = Field(..., description="Transaction timestamp (UTC)")
    from_address: str = Field(..., description="Sender wallet address")
    to_address: str = Field(..., description="Recipient wallet address")
    asset: str = Field(..., description="Asset symbol (e.g. USDT, TRX, ETH)")
    amount: float = Field(..., ge=0.0, description="Transfer amount in human-readable units")
    token_contract: Optional[str] = Field(None, description="Smart contract address for token transfers")
    transaction_type: str = Field("TRANSFER", description="Type of transaction (TRANSFER, CALL, etc.)")
    status: str = Field("SUCCESS", description="Transaction execution status (SUCCESS, FAILED, PENDING)")
    source_provider: str = Field(..., description="Data provider source (e.g. TronGrid, Etherscan)")
    explorer_url: str = Field(..., description="Direct block explorer URL for verification")

    model_config = ConfigDict(from_attributes=True)


class NormalizedTransactionCreate(NormalizedTransactionBase):
    case_id: Optional[str] = Field(None, description="Optional case identifier associated with transaction")


class NormalizedTransactionRead(NormalizedTransactionBase):
    id: str
    case_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
