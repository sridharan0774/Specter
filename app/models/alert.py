from sqlalchemy import Column, String, JSON, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Alert(Base, TimestampMixin):
    """Database model for storing High-Velocity & Typology Alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False, index=True)  # HIGH_VELOCITY, TYPOLOGY_PEEL_CHAIN, etc.
    severity = Column(String(32), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    explanation = Column(Text, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    supporting_tx_hashes = Column(JSON, nullable=False, default=list)
    supporting_wallets = Column(JSON, nullable=False, default=list)

    case = relationship("Case", back_populates="alerts")
