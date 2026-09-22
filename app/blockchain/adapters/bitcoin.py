import re
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.blockchain.adapters.base import BlockchainAdapter
from app.core.config import settings
from app.schemas.transaction import NormalizedTransactionBase

logger = logging.getLogger("specter.bitcoin")


class BitcoinAdapter(BlockchainAdapter):
    """
    Adapter for Bitcoin UTXO blockchain ingestion via Mempool.space REST API.
    Handles UTXO multi-input / multi-output fund flow mapping, Common-Input Ownership Heuristics,
    persistent HTTP connection pooling, and Satoshi exact Decimal conversion.
    """

    BASE_URL = "https://mempool.space/api"
    EXPLORER_BASE_URL = "https://mempool.space"
    # Validates Legacy (1...), P2SH (3...), Native SegWit (bc1q...), and Taproot (bc1p...)
    ADDRESS_REGEX = re.compile(r"^(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{8,87})$")

    def __init__(self, base_url: Optional[str] = None, timeout: float = 12.0):
        if base_url is not None:
            self.api_url = base_url
        else:
            self.api_url = getattr(settings, "MEMPOOL_API_URL", self.BASE_URL)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Returns or initializes shared connection-pooled AsyncClient to prevent socket descriptor exhaustion."""
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            self._client = httpx.AsyncClient(timeout=self.timeout, limits=limits)
        return self._client

    async def close(self):
        """Gracefully close HTTP client pool if active."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @property
    def chain_name(self) -> str:
        return "BITCOIN"

    @property
    def status_state(self) -> str:
        if self.api_url and str(self.api_url).strip():
            return "OPERATIONAL"
        return "ADAPTER IMPLEMENTED — PROVIDER CONFIGURATION REQUIRED"

    def validate_address(self, address: str) -> bool:
        if not address or not isinstance(address, str):
            return False
        return bool(self.ADDRESS_REGEX.match(address.strip()))

    def get_explorer_url(self, tx_hash: str) -> str:
        return f"{self.EXPLORER_BASE_URL}/tx/{tx_hash}"

    def get_address_explorer_url(self, address: str) -> str:
        return f"{self.EXPLORER_BASE_URL}/address/{address}"

    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.validate_address(address):
            return []

        url = f"{self.api_url}/address/{address.strip()}/txs"
        try:
            client = self._get_client()
            resp = await client.get(url)
            if resp.status_code == 200:
                raw_txs = resp.json()
                return raw_txs[:limit]
        except Exception as e:
            logger.warning(f"Error fetching Bitcoin transactions from Mempool.space: {e}")

        return []

    async def get_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = None,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Bitcoin native layer has no smart contract ERC-20 equivalent; delegates to get_transactions."""
        return await self.get_transactions(address, limit, min_timestamp, max_timestamp)

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        url = f"{self.api_url}/tx/{tx_hash.strip()}"
        try:
            client = self._get_client()
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Error fetching Bitcoin transaction {tx_hash}: {e}")
        return None

    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> NormalizedTransactionBase:
        """
        Maps a Bitcoin UTXO raw transaction into common NormalizedTransactionBase representation.
        Applies Common-Input Ownership Heuristics across all vin inputs and converts Satoshis to exact 8-decimal BTC.
        """
        tx_hash = raw_tx.get("txid") or raw_tx.get("hash", "")
        status_info = raw_tx.get("status", {})
        block_height = status_info.get("block_height")
        block_time = status_info.get("block_time")

        dt = datetime.fromtimestamp(block_time, tz=timezone.utc) if block_time else datetime.now(timezone.utc)

        # Extract ALL input addresses (Common-Input Ownership Heuristic for UTXO clustering)
        input_addresses: List[str] = []
        vins = raw_tx.get("vin", [])
        if vins and isinstance(vins, list):
            for vin_item in vins:
                prevout = vin_item.get("prevout", {})
                script_addr = prevout.get("scriptpubkey_address")
                if script_addr and script_addr not in input_addresses:
                    input_addresses.append(script_addr)

        primary_from_address = input_addresses[0] if input_addresses else "UNKNOWN_BTC_SENDER"

        # Extract primary output recipient and total satoshis (Satoshis -> BTC, exact Decimal precision)
        to_address = "UNKNOWN_BTC_RECIPIENT"
        total_satoshis = 0
        vouts = raw_tx.get("vout", [])
        if vouts and isinstance(vouts, list):
            for v in vouts:
                script_addr = v.get("scriptpubkey_address")
                val_sat = int(v.get("value", 0))
                if script_addr and script_addr not in input_addresses:
                    to_address = script_addr
                    total_satoshis = val_sat
                    break
            if to_address == "UNKNOWN_BTC_RECIPIENT" and vouts:
                to_address = vouts[0].get("scriptpubkey_address", "UNKNOWN_BTC_RECIPIENT")
                total_satoshis = int(vouts[0].get("value", 0))

        # Convert Satoshis to BTC with exact 8-decimal forensic precision
        btc_dec = (Decimal(str(total_satoshis)) / Decimal("100000000")).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        btc_amount = float(btc_dec)

        return NormalizedTransactionBase(
            chain=self.chain_name,
            tx_hash=tx_hash,
            block_number=block_height,
            timestamp=dt,
            from_address=primary_from_address,
            to_address=to_address,
            asset="BTC",
            amount=btc_amount,
            token_contract=None,
            transaction_type="UTXO_TRANSFER",
            status="SUCCESS" if status_info.get("confirmed", True) else "PENDING",
            source_provider="Mempool.space",
            explorer_url=self.get_explorer_url(tx_hash),
        )

    def normalize_utxo_outputs(self, raw_tx: Dict[str, Any]) -> List[NormalizedTransactionBase]:
        """
        Extracted UTXO normalization mapping each vout output into a separate NormalizedTransactionBase
        to preserve complete multi-output fund flow and change outputs.
        """
        normalized_list = []
        tx_hash = raw_tx.get("txid") or raw_tx.get("hash", "")
        status_info = raw_tx.get("status", {})
        block_height = status_info.get("block_height")
        block_time = status_info.get("block_time")

        dt = datetime.fromtimestamp(block_time, tz=timezone.utc) if block_time else datetime.now(timezone.utc)

        # Extract input addresses
        input_addresses: List[str] = []
        vins = raw_tx.get("vin", [])
        if vins and isinstance(vins, list):
            for vin_item in vins:
                prevout = vin_item.get("prevout", {})
                script_addr = prevout.get("scriptpubkey_address")
                if script_addr and script_addr not in input_addresses:
                    input_addresses.append(script_addr)

        primary_from_address = input_addresses[0] if input_addresses else "UNKNOWN_BTC_SENDER"

        vouts = raw_tx.get("vout", [])
        for out_idx, v in enumerate(vouts):
            dest_addr = v.get("scriptpubkey_address", f"UNKNOWN_VOUT_{out_idx}")
            val_sat = int(v.get("value", 0))
            btc_dec = (Decimal(str(val_sat)) / Decimal("100000000")).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
            btc_amt = float(btc_dec)

            normalized_list.append(
                NormalizedTransactionBase(
                    chain=self.chain_name,
                    tx_hash=f"{tx_hash}:{out_idx}",
                    block_number=block_height,
                    timestamp=dt,
                    from_address=primary_from_address,
                    to_address=dest_addr,
                    asset="BTC",
                    amount=btc_amt,
                    token_contract=None,
                    transaction_type="UTXO_TRANSFER",
                    status="SUCCESS" if status_info.get("confirmed", True) else "PENDING",
                    source_provider="Mempool.space",
                    explorer_url=self.get_explorer_url(tx_hash),
                )
            )

        return normalized_list
