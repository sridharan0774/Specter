from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.schemas.transaction import NormalizedTransactionBase


class BlockchainAdapter(ABC):
    """
    Abstract Base Class for chain-agnostic blockchain data adapters.
    Every chain implementation (TRON, EVM, etc.) must implement these methods.
    """

    @property
    @abstractmethod
    def chain_name(self) -> str:
        """Return canonical chain name (e.g. TRON, ETHEREUM, POLYGON, BSC)."""
        pass

    @abstractmethod
    def validate_address(self, address: str) -> bool:
        """
        Validate whether string is a syntactically valid address for this chain.
        """
        pass

    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw native transactions for address from public provider.
        """
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
        """
        Fetch raw token transfer logs for address from public provider.
        """
        pass

    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed raw data for a specific transaction hash.
        """
        pass

    @abstractmethod
    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> NormalizedTransactionBase:
        """
        Convert chain-specific raw transaction dict into common NormalizedTransaction schema.
        """
        pass

    @abstractmethod
    def get_explorer_url(self, tx_hash: str) -> str:
        """
        Return public block explorer URL for a transaction hash.
        """
        pass

    @abstractmethod
    def get_address_explorer_url(self, address: str) -> str:
        """
        Return public block explorer URL for an address.
        """
        pass
