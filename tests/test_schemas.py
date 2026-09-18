from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.schemas.transaction import NormalizedTransactionBase
from app.schemas.case import CaseCreate
from app.schemas.trace import TraceRequest


def test_normalized_transaction_schema_valid():
    tx_data = {
        "chain": "TRON",
        "tx_hash": "f29a0b1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "block_number": 60123456,
        "timestamp": datetime.now(timezone.utc),
        "from_address": "TMuA6YqJe5xcZzyaBiYehHiFGiGXD3yMUT",
        "to_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "asset": "USDT",
        "amount": 100.0,
        "token_contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "transaction_type": "TRANSFER",
        "status": "SUCCESS",
        "source_provider": "TronGrid",
        "explorer_url": "https://tronscan.org/#/transaction/f29a0b1234567890abcdef",
    }
    tx = NormalizedTransactionBase(**tx_data)
    assert tx.chain == "TRON"
    assert tx.amount == 100.0


def test_normalized_transaction_schema_invalid_amount():
    tx_data = {
        "chain": "TRON",
        "tx_hash": "hash123",
        "block_number": 100,
        "timestamp": datetime.now(timezone.utc),
        "from_address": "addr1",
        "to_address": "addr2",
        "asset": "USDT",
        "amount": -50.0,  # Negative amount must fail ge=0.0
        "source_provider": "TronGrid",
        "explorer_url": "https://tronscan.org/#/transaction/hash123",
    }
    with pytest.raises(ValidationError):
        NormalizedTransactionBase(**tx_data)


def test_case_create_schema():
    case_in = CaseCreate(
        investigator_id="AGENT_X",
        reported_wallet="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        chain="TRON",
        asset="USDT",
        description="Initial suspicious transfer investigation",
    )
    assert case_in.investigator_id == "AGENT_X"
    assert case_in.chain == "TRON"


def test_trace_request_schema():
    trace_req = TraceRequest(
        starting_wallet="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        chain="TRON",
        asset_filter="USDT",
        max_hops=3,
        minimum_transfer_value=50.0,
    )
    assert trace_req.max_hops == 3
    assert trace_req.minimum_transfer_value == 50.0
