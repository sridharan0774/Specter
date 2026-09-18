import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class InvestigationJob(Base, TimestampMixin):
    """Database model for tracking investigation pipeline state machine execution."""
    __tablename__ = "investigation_jobs"

    job_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    target_wallet = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, default="TRON")
    asset = Column(String(32), nullable=False, default="USDT")
    status = Column(String(32), nullable=False, default="QUEUED", index=True)
    progress_percent = Column(Float, nullable=False, default=0.0)
    current_stage = Column(String(64), nullable=False, default="QUEUED")
    parameters_snapshot = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", backref="investigation_jobs")


class InvestigationSnapshot(Base, TimestampMixin):
    """Database model for storing immutable reproducible snapshots of trace graph state and intelligence versioning."""
    __tablename__ = "investigation_snapshots"

    snapshot_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("investigation_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    target_wallet = Column(String(128), nullable=False)
    chain = Column(String(32), nullable=False, default="TRON")
    asset = Column(String(32), nullable=False, default="USDT")
    parameters = Column(JSON, nullable=False, default=dict)
    trace_graph_snapshot = Column(JSON, nullable=False, default=dict)
    engine_version = Column(String(32), nullable=False, default="1.0.0")
    scoring_model_version = Column(String(32), nullable=False, default="v1.0")
    source_intelligence_version = Column(String(32), nullable=False, default="v1.0.2026")
    retrieved_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    job = relationship("InvestigationJob", backref="snapshot")
