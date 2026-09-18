import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Finding(Base, TimestampMixin):
    """Database model for high-level analytical findings derived during an investigation."""
    __tablename__ = "findings"

    finding_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("investigation_jobs.job_id", ondelete="CASCADE"), nullable=True, index=True)
    finding_type = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False, default="MODERATE")
    confidence = Column(Float, nullable=False, default=1.0)
    supporting_evidence_ids = Column(JSON, nullable=False, default=list)
    metadata_json = Column(JSON, nullable=False, default=dict)

    case = relationship("Case", backref="findings")
