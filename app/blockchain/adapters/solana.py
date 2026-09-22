import re
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.blockchain.adapters.base import BlockchainAdapter
from app.core.config import settings
from app.schemas.transaction import NormalizedTransactionBase

logger = logging.getLogger("specter.solana")

SOL_USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class SolanaAdapter(BlockchainAdapter):
    """
    Adapter for Solana blockchain ingestion via Solscan REST API / Solana RPC node.
    Supports native SOL transfers and SPL token transfers (USDT, USDC).
    """

    BASE_URL = "https://public-api.solscan.io"
    EXPLORER_BASE_URL = "https://solscan.io"
    # Solana Base58 public key validation (32 to 44 characters)
    ADDRESS_REGEX = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

    def __init__(self, api_key: Optional[str] = None, rpc_url: Optional[str] = None, timeout: float = 12.0):
        self.api_key = api_key or getattr(settings, "SOLSCAN_API_KEY", None)
        self.rpc_url = rpc_url or getattr(settings, "SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.timeout = timeout

    @property
    def chain_name(self) -> str:
        return "SOLANA"

    @property
    def status_state(self) -> str:
        return "OPERATIONAL" if (self.api_key or self.rpc_url) else "ADAPTER IMPLEMENTED — PROVIDER CONFIGURATION REQUIRED"

    def validate_address(self, address: str) -> bool:
        if not address or not isinstance(address, str):
            return False
        return bool(self.ADDRESS_REGEX.match(address.strip()))

    def get_explorer_url(self, tx_hash: str) -> str:
        return f"{self.EXPLORER_BASE_URL}/tx/{tx_hash}"

    def get_address_explorer_url(self, address: str) -> str:
        return f"{self.EXPLORER_BASE_URL}/account/{address}"

    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.validate_address(address):
            return []

        url = f"{self.BASE_URL}/account/transactions"
        params = {"account": address.strip(), "limit": min(limit, 50)}
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["token"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Error calling Solscan transactions API: {e}")

        return []

    async def get_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = SOL_USDT_MINT,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.validate_address(address):
            return []

        url = f"{self.BASE_URL}/account/splTransfers"
        params = {"account": address.strip(), "limit": min(limit, 50)}
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["token"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Error calling Solscan SPL transfers API: {e}")

        return []

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/transaction/{tx_hash.strip()}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["token"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"Error calling Solscan get_transaction: {e}")

        return None

    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> NormalizedTransactionBase:
        tx_hash = raw_tx.get("txHash") or raw_tx.get("signature", "")
        token_symbol = raw_tx.get("symbol") or raw_tx.get("tokenSymbol", "SOL")
        asset = token_symbol.upper()
        decimals = int(raw_tx.get("decimals", 9 if asset == "SOL" else 6))
        token_contract = raw_tx.get("tokenAddress") or raw_tx.get("mint")

        raw_val = str(raw_tx.get("amount", raw_tx.get("lamport", "0")))
        try:
            dec_val = Decimal(raw_val)
            # Solscan amount is often pre-divided or in raw smallest units
            if dec_val > Decimal("1000000"):
                amount = float(dec_val / (Decimal(10) ** decimals))
            else:
                amount = float(dec_val)
        except Exception:
            amount = 0.0

        raw_ts = int(raw_tx.get("blockTime", raw_tx.get("blockTime", 0)))
        dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc) if raw_ts > 0 else datetime.now(timezone.utc)

        block_num = int(raw_tx.get("slot", 0)) if raw_tx.get("slot") else None

        return NormalizedTransactionBase(
            chain=self.chain_name,
            tx_hash=tx_hash,
            block_number=block_num,
            timestamp=dt,
            from_address=raw_tx.get("src") or raw_tx.get("signer", [""])[0],
            to_address=raw_tx.get("dst") or raw_tx.get("owner", ""),
            asset=asset,
            amount=amount,
            token_contract=token_contract,
            transaction_type="SPL_TRANSFER" if token_contract else "TRANSFER",
            status="SUCCESS" if raw_tx.get("status") in [True, "Success", "SUCCESS", None] else "FAILED",
            source_provider="Solscan",
            explorer_url=self.get_explorer_url(tx_hash),
        )
