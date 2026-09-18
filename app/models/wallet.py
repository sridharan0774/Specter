from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from app.core.database import Base
from app.models.base import TimestampMixin


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    id = Column(String(160), primary_key=True)  # Format: {chain}_{address}
    address = Column(String(128), nullable=False, index=True)
    chain = Column(String(32), nullable=False, index=True)
    entity_label = Column(String(128), nullable=True)
    entity_type = Column(String(64), nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    total_incoming = Column(Float, default=0.0)
    total_outgoing = Column(Float, default=0.0)
    tx_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_wallet_chain_addr", "chain", "address", unique=True),
    )
