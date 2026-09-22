from sqlalchemy import Column, String, JSON, Text, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class RiskAssessmentRecord(Base, TimestampMixin):
    """Database model for storing persistent Explainable Graph Risk Engine (EGRE_V1) assessments."""
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), nullable=True, index=True)
    starting_wallet = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, default="TRON")
    asset = Column(String(32), nullable=False, default="USDT")
    
    risk_score = Column(Float, nullable=True)
    raw_risk_score = Column(Float, nullable=True)
    contextual_risk_score = Column(Float, nullable=True)
    risk_level = Column(String(32), nullable=True)
    assessment_status = Column(String(64), nullable=False, default="ASSESSED")
    calculation_version = Column(String(32), nullable=False, default="EGRE_V1")
    
    dimension_scores = Column(JSON, nullable=False, default=dict)
    indicators = Column(JSON, nullable=False, default=list)
    component_contributions = Column(JSON, nullable=False, default=dict)
    contributing_factors = Column(JSON, nullable=False, default=list)
    false_positive_mitigations = Column(JSON, nullable=False, default=list)
    
    case = relationship("Case")
