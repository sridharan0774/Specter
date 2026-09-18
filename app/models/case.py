import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.models.base import TimestampMixin


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    case_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigator_id = Column(String(100), nullable=False, index=True)
    reported_wallet = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, index=True)
    asset = Column(String(32), nullable=False, default="USDT")
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)
    description = Column(Text, nullable=True)

    # Relationships
    transactions = relationship("NormalizedTransaction", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="case", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="case", cascade="all, delete-orphan")
    vasp_candidates = relationship("VASPCandidate", back_populates="case", cascade="all, delete-orphan")
    vasp_attributions = relationship("VASPAttribution", back_populates="case", cascade="all, delete-orphan")
