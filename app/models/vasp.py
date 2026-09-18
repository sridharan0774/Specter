import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class VASPRecord(Base, TimestampMixin):
    """Database model for known VASP / Entity Intelligence with source provenance."""
    __tablename__ = "vasp_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, index=True)
    entity_name = Column(String(128), nullable=False, index=True)
    entity_role = Column(String(64), nullable=False, default="VASP", index=True)  # VASP, TOKEN_ISSUER, TOKEN_CONTRACT, INFRASTRUCTURE
    entity_type = Column(String(64), nullable=False)  # VASP, EXCHANGE, CUSTODIAL, DEPOSIT_WALLET, HOT_WALLET, MIXER, BRIDGE, DEFI
    label_type = Column(String(64), nullable=False)  # public_address_label, verified_deposit_label, hot_wallet_label, cluster_label
    source = Column(String(128), nullable=False)  # Research or intelligence provider name
    source_url = Column(String(512), nullable=True)  # Reference URL for intelligence provenance
    source_reference = Column(String(256), nullable=True)  # Specific dataset ID or advisory reference
    source_quality_level = Column(Integer, nullable=False, default=3)  # Level 1 (Official) to Level 5 (Unverified)
    confidence = Column(Float, nullable=False, default=1.0)  # Source confidence (0.0 - 1.0)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    @property
    def is_attributable_vasp(self) -> bool:
        """
        True ONLY for actual VASP / exchange / custodial services.
        Explicitly excludes token contracts, token issuers, and general blockchain infrastructure.
        The USDT token contract (TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t) is strictly barred.
        """
        clean_addr = (self.address or "").strip().upper()
        if clean_addr == "TR7NHQJEKXGTCI8Q8ZY4PL8OTSZGJLJ6T":
            return False

        role = (getattr(self, "entity_role", None) or "VASP").upper()
        if role in ("TOKEN_CONTRACT", "TOKEN_ISSUER", "INFRASTRUCTURE"):
            return False

        etype = (self.entity_type or "").upper()
        if etype in ("TOKEN_CONTRACT", "TOKEN_ISSUER", "CONTRACT", "INFRASTRUCTURE"):
            return False

        return role in ("VASP", "EXCHANGE", "CUSTODIAL") or etype in ("VASP", "EXCHANGE", "CUSTODIAL", "DEPOSIT_WALLET", "HOT_WALLET")


class VASPAttribution(Base, TimestampMixin):
    """Database model for storing VASP Attribution evaluation results."""
    __tablename__ = "vasp_attributions"

    attribution_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="SET NULL"), nullable=True, index=True)
    trace_id = Column(String(36), ForeignKey("trace_runs.trace_id", ondelete="CASCADE"), nullable=False, index=True)

    candidate_name = Column(String(128), nullable=False, index=True)
    candidate_entity_id = Column(String(64), nullable=True)
    entity_role = Column(String(64), nullable=False, default="VASP")
    endpoint_address = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, default="TRON")
    endpoint_hop_distance = Column(Integer, nullable=False, default=1)
    match_position = Column(String(64), nullable=False, default="TERMINAL_ENDPOINT")  # TERMINAL_ENDPOINT or INTERMEDIATE_ASSOCIATION
    is_terminal_endpoint = Column(Integer, nullable=False, default=1)  # 1 = True, 0 = False
    value_transferred = Column(Float, nullable=True)
    value_retention_percent = Column(Float, nullable=True)
    temporal_proximity_seconds = Column(Float, nullable=True)
    path_convergence_count = Column(Integer, nullable=False, default=1)

    attribution_type = Column(String(64), nullable=False, default="UNRESOLVED")
    source_confidence = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    attribution_confidence = Column(Float, nullable=False, default=0.0)  # 0 - 100
    confidence_band = Column(String(32), nullable=False, default="INSUFFICIENT")  # HIGH, MODERATE, LOW, INSUFFICIENT

    score_components = Column(JSON, nullable=False, default=dict)
    evidence_summary = Column(JSON, nullable=False, default=dict)
    supporting_transactions = Column(JSON, nullable=False, default=list)
    supporting_wallets = Column(JSON, nullable=False, default=list)

    scoring_model_version = Column(String(32), nullable=False, default="vasp-score-v1")
    evaluated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    case = relationship("Case", back_populates="vasp_attributions")
    trace_run = relationship("TraceRun")


class VASPCandidate(Base, TimestampMixin):
    """Database model for storing VASP candidates ranked for a specific case (Legacy compatibility)."""
    __tablename__ = "vasp_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_vasp = Column(String(128), nullable=False)
    confidence_score = Column(Float, nullable=False)
    component_scores = Column(JSON, nullable=False)
    supporting_evidence = Column(JSON, nullable=False)
    transaction_path = Column(JSON, nullable=False)
    relevant_wallets = Column(JSON, nullable=False)
    source_labels = Column(JSON, nullable=False)

    case = relationship("Case", back_populates="vasp_candidates")

