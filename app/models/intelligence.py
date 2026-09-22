import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class CrossChainRelationship(Base, TimestampMixin):
    """
    Database model for cross-chain fund transfers, bridge interactions, and service relationships.
    Preserves chain boundaries, source/destination tx hashes, service entities, confidence, and provenance.
    """
    __tablename__ = "cross_chain_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relationship_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=True, index=True)
    
    source_chain = Column(String(32), nullable=False, index=True)
    source_address = Column(String(128), nullable=False, index=True)
    source_tx_hash = Column(String(128), nullable=False)
    
    service_entity = Column(String(128), nullable=False, index=True)  # e.g., Allbridge, Stargate, Portal, ChangeNOW
    bridge_name = Column(String(128), nullable=True)
    
    destination_chain = Column(String(32), nullable=False, index=True)
    destination_address = Column(String(128), nullable=False, index=True)
    destination_tx_hash = Column(String(128), nullable=True)
    
    relationship_type = Column(String(64), nullable=False, default="BRIDGE_TRANSFER")  # BRIDGE_TRANSFER, CROSS_CHAIN_SWAP, SERVICE_TRANSFER, UNKNOWN
    verification_status = Column(String(32), nullable=False, default="VERIFIED")  # VERIFIED, ANALYTICAL, UNVERIFIED, UNKNOWN
    confidence = Column(Float, nullable=False, default=1.0)
    
    asset_sent = Column(String(32), nullable=True)
    amount_sent = Column(Float, nullable=True)
    asset_received = Column(String(32), nullable=True)
    amount_received = Column(Float, nullable=True)
    
    evidence_summary = Column(JSON, nullable=False, default=list)
    provenance = Column(String(256), nullable=False)
    source_url = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)

    case = relationship("Case")


class PatternObservation(Base, TimestampMixin):
    """
    Database model for storing analytical transaction pattern indications (e.g. Mixer-like activity, Fan-out, Peeling).
    Strictly distinguishes ANALYTICAL indications from VERIFIED entity identities.
    """
    __tablename__ = "pattern_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    observation_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=True, index=True)
    trace_id = Column(String(36), ForeignKey("trace_runs.trace_id", ondelete="CASCADE"), nullable=True, index=True)
    
    target_wallet = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, default="TRON")
    
    pattern_type = Column(String(64), nullable=False, index=True)  # POTENTIAL_MIXER_LIKE_ACTIVITY, PEELING_CHAIN, FAN_OUT_DISPERSION, RAPID_CONSOLIDATION
    verification_status = Column(String(32), nullable=False, default="ANALYTICAL")  # Strictly ANALYTICAL (never CONFIRMED without verified DB seed)
    confidence = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    confidence_band = Column(String(32), nullable=False, default="MODERATE")
    
    indicator_values = Column(JSON, nullable=False, default=dict)  # structural metrics (e.g. fan_out_branches, delta_t, equal_split_ratio)
    supporting_transactions = Column(JSON, nullable=False, default=list)
    supporting_wallets = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=False)
    
    observed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case")
    trace_run = relationship("TraceRun")
