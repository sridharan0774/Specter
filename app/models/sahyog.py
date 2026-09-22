from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class SahyogRequest(Base):
    """
    SQLAlchemy model for persisting SAHYOG Action Center legal enforcement requests
    (Disclosure Requests & Asset Preservation / Freeze Requests).
    
    Status Contract:
    - Status: DRAFT_REQUIRES_AUTHORISED_REVIEW
    - Integration Status: READY_FOR_AUTHORISED_API_INTEGRATION
    """
    __tablename__ = "sahyog_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), unique=True, index=True, nullable=False)
    case_id = Column(String(64), ForeignKey("cases.case_id"), index=True, nullable=False)
    job_id = Column(String(64), nullable=True, index=True)
    
    request_type = Column(String(64), nullable=False)  # DISCLOSURE_REQUEST | ASSET_PRESERVATION_OR_FREEZE_REQUEST
    status = Column(String(64), nullable=False, default="DRAFT_REQUIRES_AUTHORISED_REVIEW")
    package_version = Column(String(32), nullable=False, default="1.0")
    integration_status = Column(String(64), nullable=False, default="READY_FOR_AUTHORISED_API_INTEGRATION")
    
    target_wallet = Column(String(128), nullable=False)
    chain = Column(String(32), nullable=False, default="TRON")
    asset = Column(String(32), nullable=False, default="USDT")
    
    attributed_vasp = Column(String(128), nullable=True)
    endpoint_address = Column(String(128), nullable=True)
    attribution_score = Column(Float, nullable=False, default=0.0)
    confidence_level = Column(String(32), nullable=False, default="HIGH")
    hop_distance = Column(Integer, nullable=False, default=0)
    endpoint_status = Column(String(64), nullable=False, default="TERMINAL ENDPOINT")
    
    validation_result = Column(JSON, nullable=True)
    request_data = Column(JSON, nullable=False)
    evidence_chain = Column(JSON, nullable=True)
    evidence_snapshot_reference = Column(String(128), nullable=True)
    exported_path = Column(String(255), nullable=True)
    investigator_id = Column(String(64), nullable=False, default="INV-AUTOMATED-001")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    case = relationship("Case", back_populates="sahyog_requests")
