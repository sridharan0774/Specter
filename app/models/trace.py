import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class TraceRun(Base, TimestampMixin):
    """Database model for storing a Multi-Hop Trace execution run."""
    __tablename__ = "trace_runs"

    trace_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="SET NULL"), nullable=True, index=True)
    starting_wallet = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, default="TRON")
    asset = Column(String(32), nullable=False, default="USDT")
    max_hops = Column(Integer, nullable=False, default=5)
    parameters = Column(JSON, nullable=False, default=dict)
    
    status = Column(String(32), nullable=False, default="VALIDATING", index=True)
    truncated = Column(Boolean, nullable=False, default=False)
    truncation_reason = Column(Text, nullable=True)
    
    total_wallets_discovered = Column(Integer, nullable=False, default=0)
    total_transactions_analyzed = Column(Integer, nullable=False, default=0)
    total_edges_discovered = Column(Integer, nullable=False, default=0)
    total_paths_found = Column(Integer, nullable=False, default=0)
    
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Relationships
    nodes = relationship("TraceNode", back_populates="trace_run", cascade="all, delete-orphan")
    edges = relationship("TraceEdge", back_populates="trace_run", cascade="all, delete-orphan")
    paths = relationship("TracePath", back_populates="trace_run", cascade="all, delete-orphan")


class TraceNode(Base, TimestampMixin):
    """Database model for a wallet node discovered during tracing."""
    __tablename__ = "trace_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(36), ForeignKey("trace_runs.trace_id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_address = Column(String(128), nullable=False, index=True)
    hop = Column(Integer, nullable=False, default=0)
    first_discovered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    transaction_count = Column(Integer, nullable=False, default=0)
    is_starting_wallet = Column(Boolean, nullable=False, default=False)

    trace_run = relationship("TraceRun", back_populates="nodes")


class TraceEdge(Base, TimestampMixin):
    """Database model for a directed transfer edge between wallets."""
    __tablename__ = "trace_edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(36), ForeignKey("trace_runs.trace_id", ondelete="CASCADE"), nullable=False, index=True)
    from_wallet = Column(String(128), nullable=False, index=True)
    to_wallet = Column(String(128), nullable=False, index=True)
    tx_hash = Column(String(128), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    asset = Column(String(32), nullable=False, default="USDT")
    timestamp = Column(DateTime, nullable=False, index=True)
    hop = Column(Integer, nullable=False)
    delta_t_seconds = Column(Float, nullable=True)
    explorer_url = Column(String(512), nullable=False)

    trace_run = relationship("TraceRun", back_populates="edges")


class TracePath(Base, TimestampMixin):
    """Database model for a reconstructed multi-hop flow path."""
    __tablename__ = "trace_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(36), ForeignKey("trace_runs.trace_id", ondelete="CASCADE"), nullable=False, index=True)
    path_id = Column(String(64), nullable=False, index=True)
    wallet_sequence = Column(JSON, nullable=False)
    edge_sequence = Column(JSON, nullable=False)
    hop_count = Column(Integer, nullable=False)
    initial_amount = Column(Float, nullable=False)
    final_amount = Column(Float, nullable=False)
    value_retention_percent = Column(Float, nullable=False)
    elapsed_time_seconds = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    relevance_explanation = Column(JSON, nullable=False, default=list)
    cycle_detected = Column(Boolean, nullable=False, default=False)

    trace_run = relationship("TraceRun", back_populates="paths")
