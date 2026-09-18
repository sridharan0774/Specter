import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone
import httpx

from app.blockchain.tron import TronAdapter, TRON_USDT_CONTRACT
from app.schemas.transaction import NormalizedTransactionBase


# =====================================================================
# 1. UNIT TESTS
# =====================================================================

def test_tron_address_validation():
    adapter = TronAdapter()
    assert adapter.validate_address("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t") is True
    assert adapter.validate_address("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL") is True
    assert adapter.validate_address("TJCnKsPa7y5okkXvQWBzxaZ2MJK7JBFZ12") is True

    # Invalid addresses
    assert adapter.validate_address("0x71C7656EC7ab88b098defB751B7401B5f6d8976F") is False  # EVM address
    assert adapter.validate_address("TR7NHqjeKQxGTCi8q8ZY4pL") is False  # Too short
    assert adapter.validate_address("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t000") is False  # Too long
    assert adapter.validate_address("XR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t") is False  # Does not start with T
    assert adapter.validate_address("") is False
    assert adapter.validate_address(None) is False


def test_explorer_urls():
    adapter = TronAdapter()
    tx_hash = "3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227"
    addr = "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"

    assert adapter.get_explorer_url(tx_hash) == f"https://tronscan.org/#/transaction/{tx_hash}"
    assert adapter.get_address_explorer_url(addr) == f"https://tronscan.org/#/address/{addr}"


def test_normalization_and_amount_conversion():
    adapter = TronAdapter()
    raw_trc20_tx = {
        "transaction_id": "3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227",
        "token_info": {
            "symbol": "USDT",
            "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "decimals": 6,
            "name": "Tether USD"
        },
        "block_timestamp": 1789281606000,
        "from": "TZ5g3BDMPqxwuGSaiqVdyBYpkrMf9teT5U",
        "to": "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        "type": "Transfer",
        "value": "752000000"
    }

    norm = adapter.normalize_transaction(raw_trc20_tx)

    assert isinstance(norm, NormalizedTransactionBase)
    assert norm.chain == "TRON"
    assert norm.tx_hash == "3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227"
    assert norm.asset == "USDT"
    assert norm.amount == 752.0  # 752000000 / 10^6
    assert norm.from_address == "TZ5g3BDMPqxwuGSaiqVdyBYpkrMf9teT5U"
    assert norm.to_address == "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"
    assert norm.token_contract == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    assert norm.source_provider == "TronGrid"
    assert norm.explorer_url == "https://tronscan.org/#/transaction/3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227"


# =====================================================================
# 2. MOCK PROVIDER TESTS
# =====================================================================

@pytest.mark.anyio
async def test_mock_successful_response():
    adapter = TronAdapter()
    mock_payload = {
        "success": True,
        "data": [
            {
                "transaction_id": "tx123",
                "token_info": {"symbol": "USDT", "address": TRON_USDT_CONTRACT, "decimals": 6},
                "block_timestamp": 1690000000000,
                "from": "addr1",
                "to": "addr2",
                "value": "100000000"
            }
        ],
        "meta": {"fingerprint": "fp_next"}
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload
        mock_get.return_value = mock_response

        raw_txs, fp, status = await adapter.get_token_transfers("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        
        assert status == "SUCCESS"
        assert len(raw_txs) == 1
        assert fp == "fp_next"
        assert raw_txs[0]["transaction_id"] == "tx123"


@pytest.mark.anyio
async def test_mock_empty_result():
    adapter = TronAdapter()
    mock_payload = {"success": True, "data": [], "meta": {}}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload
        mock_get.return_value = mock_response

        raw_txs, fp, status = await adapter.get_token_transfers("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        assert status == "NO_DATA"
        assert len(raw_txs) == 0
        assert fp is None


@pytest.mark.anyio
async def test_mock_malformed_response():
    adapter = TronAdapter()
    mock_payload = {"success": False, "error": "Internal error"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload
        mock_get.return_value = mock_response

        raw_txs, fp, status = await adapter.get_token_transfers("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        assert status == "MALFORMED_RESPONSE"
        assert len(raw_txs) == 0


@pytest.mark.anyio
async def test_mock_rate_limiting():
    adapter = TronAdapter(max_retries=1)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        raw_txs, fp, status = await adapter.get_token_transfers("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        assert status == "RATE_LIMITED"


@pytest.mark.anyio
async def test_mock_provider_failure():
    adapter = TronAdapter(max_retries=1)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.NetworkError("Connection refused")

        raw_txs, fp, status = await adapter.get_token_transfers("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
        assert status == "PROVIDER_UNAVAILABLE"


@pytest.mark.anyio
async def test_mock_deduplication_and_pagination():
    adapter = TronAdapter()
    
    # Page 1 payload
    page1 = {
        "success": True,
        "data": [
            {"transaction_id": "tx1", "from": "A", "to": "B", "value": "100", "token_info": {"symbol": "USDT", "decimals": 6}},
            {"transaction_id": "tx2", "from": "C", "to": "D", "value": "200", "token_info": {"symbol": "USDT", "decimals": 6}},
        ],
        "meta": {"fingerprint": "fp_2"}
    }
    # Page 2 payload (includes tx2 duplicate and tx3 new)
    page2 = {
        "success": True,
        "data": [
            {"transaction_id": "tx2", "from": "C", "to": "D", "value": "200", "token_info": {"symbol": "USDT", "decimals": 6}},
            {"transaction_id": "tx3", "from": "E", "to": "F", "value": "300", "token_info": {"symbol": "USDT", "decimals": 6}},
        ],
        "meta": {}
    }

    with patch.object(adapter, "get_token_transfers", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [
            (page1["data"], "fp_2", "SUCCESS"),
            (page2["data"], None, "SUCCESS"),
        ]

        result = await adapter.get_all_token_transfers("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL", max_pages=2)

        assert result["pages_fetched"] == 2
        assert result["records_fetched"] == 3  # tx1, tx2, tx3 (tx2 deduplicated)
        hashes = [tx.tx_hash for tx in result["transactions"]]
        assert hashes == ["tx1", "tx2", "tx3"]


# =====================================================================
# 3. LIVE API TEST
# =====================================================================

@pytest.mark.anyio
async def test_live_tron_api_real_address():
    """Live API test against a real TRON address."""
    adapter = TronAdapter()
    real_address = "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"

    result = await adapter.get_all_token_transfers(
        address=real_address,
        token_contract=TRON_USDT_CONTRACT,
        max_pages=1,
        page_size=3
    )

    assert result["status"] == "SUCCESS"
    assert result["pages_fetched"] == 1
    assert result["records_fetched"] > 0
    assert len(result["transactions"]) > 0

    first_tx = result["transactions"][0]
    assert first_tx.chain == "TRON"
    assert len(first_tx.tx_hash) == 64
    assert first_tx.asset == "USDT"
    assert first_tx.amount >= 0.0
    assert first_tx.explorer_url.startswith("https://tronscan.org/#/transaction/")
