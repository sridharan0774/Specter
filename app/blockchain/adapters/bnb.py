import re
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.blockchain.adapters.base import BlockchainAdapter
from app.core.config import settings
from app.schemas.transaction import NormalizedTransactionBase

logger = logging.getLogger("specter.bnb")

BNB_USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
BNB_BUSD_CONTRACT = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"


class BnbAdapter(BlockchainAdapter):
    """
    Adapter for BNB Smart Chain (BSC) ingestion via BscScan / BEP-20 REST provider API.
    Supports native BNB transactions and BEP-20 token transfers (USDT, BUSD).
    """

    BASE_URL = "https://api.bscscan.com/api"
    EXPLORER_BASE_URL = "https://bscscan.com"
    ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

    def __init__(self, api_key: Optional[str] = None, timeout: float = 12.0):
        self.api_key = api_key or settings.BSCSCAN_API_KEY
        self.timeout = timeout

    @property
    def chain_name(self) -> str:
        return "BNB"

    @property
    def status_state(self) -> str:
        return "OPERATIONAL" if self.api_key else "ADAPTER IMPLEMENTED — PROVIDER CONFIGURATION REQUIRED"

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
        if not self.validate_address(address) or not self.api_key:
            return []

        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": min(limit, 100),
            "sort": "desc",
            "apikey": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        return data.get("result", [])
        except Exception as e:
            logger.warning(f"Error calling BscScan API: {e}")

        return []

    async def get_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = BNB_USDT_CONTRACT,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not self.validate_address(address) or not self.api_key:
            return []

        params = {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": min(limit, 100),
            "sort": "desc",
            "apikey": self.api_key,
        }
        if token_contract:
            params["contractaddress"] = token_contract

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        return data.get("result", [])
        except Exception as e:
            logger.warning(f"Error calling BscScan token transfers API: {e}")

        return []

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        params = {
            "module": "proxy",
            "action": "eth_getTransactionByHash",
            "txhash": tx_hash,
            "apikey": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.BASE_URL, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result")
        except Exception as e:
            logger.warning(f"Error calling BscScan eth_getTransactionByHash: {e}")
        return None

    def normalize_transaction(self, raw_tx: Dict[str, Any]) -> NormalizedTransactionBase:
        tx_hash = raw_tx.get("hash") or raw_tx.get("transaction_id", "")
        asset = raw_tx.get("tokenSymbol", "BNB").upper()
        decimals = int(raw_tx.get("tokenDecimal", 18 if asset == "BNB" else 18))
        token_contract = raw_tx.get("contractAddress")

        raw_val = str(raw_tx.get("value", "0"))
        try:
            dec_val = Decimal(raw_val)
            amount = float(dec_val / (Decimal(10) ** decimals))
        except Exception:
            amount = 0.0

        raw_ts = int(raw_tx.get("timeStamp", 0))
        dt = datetime.fromtimestamp(raw_ts, tz=timezone.utc) if raw_ts > 0 else datetime.now(timezone.utc)

        block_num = int(raw_tx.get("blockNumber", 0)) if raw_tx.get("blockNumber") else None

        return NormalizedTransactionBase(
            chain=self.chain_name,
            tx_hash=tx_hash,
            block_number=block_num,
            timestamp=dt,
            from_address=raw_tx.get("from", ""),
            to_address=raw_tx.get("to", ""),
            asset=asset,
            amount=amount,
            token_contract=token_contract,
            transaction_type="BEP20_TRANSFER" if token_contract else "TRANSFER",
            status="SUCCESS" if raw_tx.get("isError", "0") == "0" else "FAILED",
            source_provider="BscScan",
            explorer_url=self.get_explorer_url(tx_hash),
        )
