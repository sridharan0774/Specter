from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class RollingWindowMetric(BaseModel):
    window_name: str = Field(..., description="Window name: 1m, 5m, 10m, 30m, 1h")
    window_seconds: int = Field(..., description="Window size in seconds")
    transfer_count: int = Field(0, description="Number of transfers inside window")
    total_amount: float = Field(0.0, description="Total asset volume moved inside window")
    unique_recipients: int = Field(0, description="Unique recipient count in window")

    model_config = ConfigDict(from_attributes=True)


class VelocityAlert(BaseModel):
    alert_id: str = Field(..., description="Unique alert identifier")
    trace_id: str = Field(..., description="Associated trace run ID")
    case_id: Optional[str] = Field(None, description="Associated case ID")
    alert_type: str = Field("HIGH_VELOCITY_MOVEMENT", description="Category of velocity alert")
    severity: str = Field(..., description="Severity level: LOW, MODERATE, HIGH, CRITICAL")
    velocity_score: float = Field(..., ge=0.0, le=100.0, description="Transparent Velocity Alert Score (0-100)")
    transfer_count: int = Field(..., description="Total transfers analyzed in high-velocity sequence")
    total_amount: float = Field(..., description="Total asset amount moved")
    duration_seconds: float = Field(..., description="Total movement duration in seconds")
    minimum_delta_t: float = Field(..., description="Shortest delta_t between successive transfers in seconds")
    average_delta_t: float = Field(..., description="Average delta_t between transfers in seconds")
    maximum_delta_t: float = Field(..., description="Longest delta_t between transfers in seconds")
    unique_recipients: int = Field(..., description="Number of unique recipient wallet addresses")
    downstream_hops: int = Field(0, description="Number of successive downstream hop transfers")
    supporting_transactions: List[str] = Field(default_factory=list, description="Hashes of supporting transactions")
    supporting_wallets: List[str] = Field(default_factory=list, description="Addresses of supporting wallets")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable alert reason codes")
    rolling_windows: Dict[str, RollingWindowMetric] = Field(default_factory=dict, description="Rolling window breakdown")
    score_components: Dict[str, float] = Field(default_factory=dict, description="Component score breakdown")
    explanation: str = Field(..., description="Analytical explanation summary")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class VelocityAnalysisResponse(BaseModel):
    trace_id: str
    case_id: Optional[str] = None
    starting_wallet: str
    chain: str = "TRON"
    asset: str = "USDT"
    has_high_velocity_pattern: bool = False
    status: str = Field(..., description="RESOLVED_ALERT or NO_HIGH_VELOCITY_PATTERN_DETECTED")
    summary: str
    alerts: List[VelocityAlert] = Field(default_factory=list)
    rolling_windows: Dict[str, RollingWindowMetric] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
