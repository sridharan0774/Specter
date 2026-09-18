from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import TimestampMixin


class EvidenceItem(Base, TimestampMixin):
    """Database model for storing verifiable findings in the Evidence Ledger."""
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    finding = Column(Text, nullable=False)
    supporting_tx_hashes = Column(JSON, nullable=False, default=list)
    supporting_addresses = Column(JSON, nullable=False, default=list)
    source = Column(String(128), nullable=False)
    retrieval_timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    scoring_factors = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.0)
    explorer_urls = Column(JSON, nullable=False, default=list)

    case = relationship("Case", back_populates="evidence_items")
