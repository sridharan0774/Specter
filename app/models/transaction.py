from sqlalchemy import Column, String, BigInteger, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class NormalizedTransaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(String(128), primary_key=True)  # Format: {chain}_{tx_hash} or composite key
    chain = Column(String(32), nullable=False, index=True)
    tx_hash = Column(String(128), nullable=False, index=True)
    block_number = Column(BigInteger, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    from_address = Column(String(128), nullable=False, index=True)
    to_address = Column(String(128), nullable=False, index=True)
    asset = Column(String(32), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    token_contract = Column(String(128), nullable=True)
    transaction_type = Column(String(32), nullable=False, default="TRANSFER")
    status = Column(String(32), nullable=False, default="SUCCESS")
    source_provider = Column(String(64), nullable=False)
    explorer_url = Column(String(512), nullable=False)

    case_id = Column(String(36), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=True, index=True)
    case = relationship("Case", back_populates="transactions")

    __table_args__ = (
        Index("idx_tx_from_to", "from_address", "to_address"),
        Index("idx_tx_chain_hash", "chain", "tx_hash"),
    )
