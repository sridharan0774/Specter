from datetime import datetime, timezone
from app.models.case import Case
from app.models.transaction import NormalizedTransaction
from app.models.wallet import Wallet
from app.models.vasp import VASPRecord, VASPCandidate
from app.models.evidence import EvidenceItem
from app.models.alert import Alert


def test_create_case_model(db):
    case = Case(
        investigator_id="INV-001",
        reported_wallet="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        chain="TRON",
        asset="USDT",
        description="Test case for TRON USDT wallet flow",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    assert case.case_id is not None
    assert case.investigator_id == "INV-001"
    assert case.reported_wallet == "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
    assert case.chain == "TRON"
    assert case.status == "ACTIVE"


def test_normalized_transaction_model(db):
    tx = NormalizedTransaction(
        id="TRON_abc123hash",
        chain="TRON",
        tx_hash="abc123hash",
        block_number=50000000,
        timestamp=datetime.now(timezone.utc),
        from_address="T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
        to_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        asset="USDT",
        amount=1500.50,
        token_contract="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        transaction_type="TRANSFER",
        status="SUCCESS",
        source_provider="TronGrid",
        explorer_url="https://tronscan.org/#/transaction/abc123hash",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    assert tx.tx_hash == "abc123hash"
    assert tx.amount == 1500.50
    assert tx.chain == "TRON"


def test_vasp_record_model(db):
    vasp = VASPRecord(
        address="TJCnKsPa7y5okkXvQWBzxaZ2MJK7JBFZ12",
        chain="TRON",
        entity_name="Binance Hot Wallet",
        entity_type="VASP",
        label_type="hot_wallet",
        source="Public Blockchain Intelligence",
        confidence=0.95,
    )
    db.add(vasp)
    db.commit()
    db.refresh(vasp)

    assert vasp.entity_name == "Binance Hot Wallet"
    assert vasp.confidence == 0.95
