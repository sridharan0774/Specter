from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class TraceRequest(BaseModel):
    starting_wallet: str = Field(..., description="Starting target address for outgoing flow trace")
    chain: str = Field("TRON", description="Blockchain network (e.g. TRON, ETHEREUM)")
    asset: str = Field("USDT", validation_alias=AliasChoices("asset", "asset_filter"), description="Asset symbol filter (e.g. USDT)")
    max_hops: int = Field(5, ge=1, le=10, description="Maximum hop depth for multi-hop traversal")
    min_transfer_amount: float = Field(0.0, ge=0.0, validation_alias=AliasChoices("min_transfer_amount", "minimum_transfer_value"), description="Minimum transfer value threshold to prune dust")
    max_transactions_per_wallet: int = Field(50, ge=1, le=200, description="Max transactions to inspect per wallet")
    max_total_transactions: int = Field(500, ge=1, le=2000, description="Hard cap on total transactions examined")
    max_children_per_node: int = Field(10, ge=1, le=50, description="Max downstream branches to expand per node")
    time_window_start: Optional[datetime] = Field(None, description="Optional start timestamp filter")
    time_window_end: Optional[datetime] = Field(None, description="Optional end timestamp filter")
    direction: str = Field("OUTGOING", description="Fund flow direction: OUTGOING or INCOMING")

    @property
    def minimum_transfer_value(self) -> float:
        return self.min_transfer_amount

    @property
    def asset_filter(self) -> str:
        return self.asset




class TraceHopItem(BaseModel):
    hop_number: int
    from_address: str
    to_address: str
    tx_hash: str
    asset: str
    amount: float
    timestamp: datetime
    block_number: Optional[int] = None
    delta_t_seconds: Optional[float] = None
    explorer_url: str

    model_config = ConfigDict(from_attributes=True)


class TracePathDetail(BaseModel):
    path_id: str
    wallet_sequence: List[str]
    hop_count: int
    initial_amount: float
    final_amount: float
    value_retention_percent: float
    elapsed_time_seconds: float
    relevance_score: float
    relevance_explanation: List[str]
    cycle_detected: bool = False
    metrics: Dict[str, Any] = Field(default_factory=dict)
    hops: List[TraceHopItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TraceResultResponse(BaseModel):
    trace_id: str
    case_id: Optional[str] = None
    starting_wallet: str
    chain: str
    asset: str
    status: str
    truncated: bool = False
    truncation_reason: Optional[str] = None
    total_wallets_discovered: int = 0
    total_transactions_analyzed: int = 0
    total_edges_discovered: int = 0
    total_paths_found: int = 0
    processing_time_seconds: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    paths: List[TracePathDetail] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Backwards compatibility aliases
HopPath = TracePathDetail
TraceResponse = TraceResultResponse

