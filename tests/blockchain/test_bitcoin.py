import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.blockchain.adapters.bitcoin import BitcoinAdapter
from app.blockchain.registry import ChainRegistry, get_adapter
from app.schemas.transaction import NormalizedTransactionBase
from app.models.transaction import NormalizedTransaction


def test_bitcoin_address_validations():
    adapter = BitcoinAdapter()

    # 1. Native SegWit (bc1q...)
    assert adapter.validate_address("bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x") is True
    assert adapter.validate_address("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq") is True

    # 2. Legacy (1...)
    assert adapter.validate_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is True

    # 3. P2SH (3...)
    assert adapter.validate_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") is True

    # 4. Invalid addresses
    assert adapter.validate_address("invalid_btc_address") is False
    assert adapter.validate_address("0x1234567890123456789012345678901234567890") is False


@pytest.mark.anyio
async def test_bitcoin_mempool_retrieval_and_utxo_normalization():
    adapter = BitcoinAdapter()
    
    # Test normalization on sample UTXO transaction payload
    sample_raw_tx = {
        "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
        "version": 1,
        "locktime": 0,
        "vin": [
            {
                "txid": "prev_tx_hash",
                "vout": 0,
                "prevout": {
                    "scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "value": 200000000,
                },
            }
        ],
        "vout": [
            {
                "scriptpubkey_address": "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x",
                "value": 150000000,
            },
            {
                "scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                "value": 49990000,
            },
        ],
        "status": {
            "confirmed": True,
            "block_height": 700000,
            "block_time": 1700000000,
        },
    }

    norm = adapter.normalize_transaction(sample_raw_tx)

    assert norm.chain == "BITCOIN"
    assert norm.tx_hash == "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
    assert norm.block_number == 700000
    assert norm.from_address == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert norm.to_address == "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x"
    assert norm.asset == "BTC"
    assert norm.amount == 1.5  # 150,000,000 Satoshis = 1.5 BTC
    assert norm.status == "SUCCESS"
    assert norm.source_provider == "Mempool.space"


from datetime import datetime, timezone

def test_bitcoin_transaction_persistence(db: Session):
    adapter = BitcoinAdapter()

    sample_tx = NormalizedTransactionBase(
        chain="BITCOIN",
        tx_hash="f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
        block_number=700000,
        timestamp=datetime.now(timezone.utc),
        from_address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        to_address="bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x",
        asset="BTC",
        amount=1.5,
        token_contract=None,
        transaction_type="UTXO_TRANSFER",
        status="SUCCESS",
        source_provider="Mempool.space",
        explorer_url="https://mempool.space/tx/f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
    )


    persisted = adapter.persist_transactions(db, [sample_tx], case_id="case-btc-test-01")

    assert len(persisted) == 1
    assert persisted[0].chain == "BITCOIN"
    assert persisted[0].asset == "BTC"
    assert persisted[0].amount == 1.5
    assert persisted[0].case_id == "case-btc-test-01"

    # Query DB to verify
    db_rec = db.query(NormalizedTransaction).filter(NormalizedTransaction.id == persisted[0].id).first()
    assert db_rec is not None
    assert db_rec.to_address == "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x"


def test_bitcoin_chain_status_operational_and_fallback():
    # 1. Operational when api_url is set
    adapter = BitcoinAdapter(base_url="https://mempool.space/api")
    assert adapter.status_state == "OPERATIONAL"

    # 2. Fallback when provider API URL is missing/empty
    adapter_no_provider = BitcoinAdapter(base_url="")
    assert adapter_no_provider.status_state == "ADAPTER IMPLEMENTED — PROVIDER CONFIGURATION REQUIRED"


def test_bitcoin_end_to_end_investigation_endpoint():
    client = TestClient(app)

    # 1. Create Case for Bitcoin
    c_res = client.post("/api/v1/cases", json={
        "reported_wallet": "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x",
        "chain": "BITCOIN",
        "asset": "BTC",
        "investigator_id": "INV-BTC-TEST",
        "description": "Bitcoin E2E Investigation Test"
    })
    assert c_res.status_code == 201
    cid = c_res.json()["case_id"]

    # 2. Execute Investigation for Bitcoin
    inv_res = client.post(f"/api/v1/cases/{cid}/investigate", json={
        "wallet": "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x",
        "chain": "BITCOIN",
        "asset": "BTC",
        "max_hops": 2,
        "investigator_id": "INV-BTC-TEST"
    })

    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "COMPLETED"
    assert inv_data["chain"] == "BITCOIN"
    assert inv_data["target_wallet"] == "bc1qyje4lr8qkqy83jaaw625ez3u58e7wyt9tw9y7x"
