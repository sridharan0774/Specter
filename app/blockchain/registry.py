import logging
from typing import Dict, Any, List, Optional, Type
from app.blockchain.adapters.base import BlockchainAdapter
from app.blockchain.adapters.tron import TronAdapter
from app.blockchain.adapters.ethereum import EthereumAdapter
from app.blockchain.adapters.bnb import BnbAdapter
from app.blockchain.adapters.polygon import PolygonAdapter
from app.blockchain.adapters.bitcoin import BitcoinAdapter
from app.blockchain.adapters.solana import SolanaAdapter

logger = logging.getLogger("specter.blockchain.registry")


class ChainRegistry:
    """
    Central Registry & Factory for Multi-Chain SPECTER Blockchain Adapters.
    Encapsulates adapter instantiation, provider status reflection, and address validation.
    """

    _REGISTRY: Dict[str, Type[BlockchainAdapter]] = {
        "TRON": TronAdapter,
        "ETHEREUM": EthereumAdapter,
        "ETH": EthereumAdapter,
        "BNB": BnbAdapter,
        "BSC": BnbAdapter,
        "POLYGON": PolygonAdapter,
        "MATIC": PolygonAdapter,
        "BITCOIN": BitcoinAdapter,
        "BTC": BitcoinAdapter,
        "SOLANA": SolanaAdapter,
        "SOL": SolanaAdapter,
    }

    @classmethod
    def get_adapter(cls, chain: str) -> BlockchainAdapter:
        """
        Instantiates and returns the designated BlockchainAdapter for a given chain name.
        Raises ValueError for unknown/unsupported networks.
        """
        if not chain or not isinstance(chain, str):
            raise ValueError("Chain identifier must be a non-empty string.")

        canonical_chain = chain.strip().upper()
        adapter_cls = cls._REGISTRY.get(canonical_chain)

        if not adapter_cls:
            supported = ", ".join(sorted(set(cls._REGISTRY.keys())))
            raise ValueError(
                f"Unsupported or unknown blockchain network '{chain}'. Supported chains: {supported}"
            )

        return adapter_cls()

    @classmethod
    def list_supported_chains(cls) -> List[Dict[str, Any]]:
        """
        Returns metadata and operational status for all registered blockchain networks.
        """
        canonical_chains = ["TRON", "ETHEREUM", "BNB", "POLYGON", "BITCOIN", "SOLANA"]
        results = []

        for name in canonical_chains:
            adapter = cls.get_adapter(name)
            results.append({
                "chain": name,
                "status": adapter.status_state,
                "is_operational": adapter.status_state == "OPERATIONAL",
                "explorer_url": adapter.get_explorer_url(""),
            })

        return results

    @classmethod
    def validate_address_for_chain(cls, chain: str, address: str) -> bool:
        """
        Validates address syntax using the designated chain's adapter rule set.
        """
        try:
            adapter = cls.get_adapter(chain)
            return adapter.validate_address(address)
        except Exception as exc:
            logger.warning(f"Address validation failed for chain '{chain}': {exc}")
            return False


def get_adapter(chain: str) -> BlockchainAdapter:
    """Global convenience helper function to obtain a chain adapter."""
    return ChainRegistry.get_adapter(chain)
