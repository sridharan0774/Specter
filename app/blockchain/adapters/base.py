from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.schemas.transaction import NormalizedTransactionBase


class BlockchainAdapter(ABC):
    """
    Abstract Base Class for chain-agnostic blockchain data adapters.
    Every chain implementation (TRON, Ethereum, BNB, Polygon, Bitcoin, Solana)
    must implement these methods to feed the normalized analytics engine.
    """

    @property
    @abstractmethod
    def chain_name(self) -> str:
        """Return canonical chain name (e.g. TRON, ETHEREUM, POLYGON, BNB, BITCOIN, SOLANA)."""
        pass

    @property
    def status_state(self) -> str:
        """
        Return operational status of adapter:
        - OPERATIONAL (Live provider active)
        - ADAPTER IMPLEMENTED — PROVIDER CONFIGURATION REQUIRED (Adapter ready, provider credentials missing)
        """
        return "OPERATIONAL"

    @abstractmethod
    def validate_address(self, address: str) -> bool:
        """Validate whether string is a syntactically valid address for this chain."""
        pass

    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw native transactions for address from public provider."""
        pass

    @abstractmethod
    async def get_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = None,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw token transfer logs for address from public provider."""
        pass

    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed raw data for a specific transaction hash."""
        pass

    @abstractmethod
    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> NormalizedTransactionBase:
        """Convert chain-specific raw transaction dict into common NormalizedTransaction schema."""
        pass

    @abstractmethod
    def get_explorer_url(self, tx_hash: str) -> str:
        """Return public block explorer URL for a transaction hash."""
        pass

    @abstractmethod
    def get_address_explorer_url(self, address: str) -> str:
        """Return public block explorer URL for an address."""
        pass

    def persist_transactions(
        self,
        db: Any,
        transactions: List[NormalizedTransactionBase],
        case_id: Optional[str] = None,
    ) -> List[Any]:
        """
        Persist normalized transactions into relational database with deterministic deduplication.
        Common implementation for all blockchain adapters (TRON, Bitcoin, Ethereum, BNB, Polygon, Solana).
        """
        from app.models.transaction import NormalizedTransaction

        persisted_records = []
        for tx in transactions:
            record_id = f"{tx.chain}_{tx.tx_hash}_{tx.from_address}_{tx.to_address}_{tx.amount}"

            existing = db.query(NormalizedTransaction).filter(NormalizedTransaction.id == record_id).first()
            if not existing:
                db_record = NormalizedTransaction(
                    id=record_id,
                    chain=tx.chain,
                    tx_hash=tx.tx_hash,
                    block_number=tx.block_number,
                    timestamp=tx.timestamp,
                    from_address=tx.from_address,
                    to_address=tx.to_address,
                    asset=tx.asset,
                    amount=tx.amount,
                    token_contract=tx.token_contract,
                    transaction_type=tx.transaction_type,
                    status=tx.status,
                    source_provider=tx.source_provider,
                    explorer_url=tx.explorer_url,
                    case_id=case_id,
                )
                db.add(db_record)
                persisted_records.append(db_record)
            else:
                if case_id and not existing.case_id:
                    existing.case_id = case_id
                persisted_records.append(existing)
        db.commit()
        return persisted_records

