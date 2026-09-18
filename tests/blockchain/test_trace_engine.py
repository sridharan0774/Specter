import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.blockchain.base import BlockchainAdapter
from app.schemas.transaction import NormalizedTransactionBase
from app.schemas.trace import TraceRequest
from app.tracing.engine import TraceEngine
from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.models.case import Case
from app.blockchain.tron.adapter import TronAdapter, TRON_USDT_CONTRACT


class MockAdapter(BlockchainAdapter):
    """Mock adapter simulating deterministic transfer topologies for unit testing."""

    def __init__(self, topology: Optional[Dict[str, List[NormalizedTransactionBase]]] = None):
        self.topology = topology or {}

    @property
    def chain_name(self) -> str:
        return "TRON"

    def validate_address(self, address: str) -> bool:
        return len(address) > 5

    def get_explorer_url(self, tx_hash: str) -> str:
        return f"https://tronscan.org/#/transaction/{tx_hash}"

    def get_address_explorer_url(self, address: str) -> str:
        return f"https://tronscan.org/#/address/{address}"

    async def get_transactions(
        self,
        address: str,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return []

    async def get_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = None,
        limit: int = 50,
        min_timestamp: Optional[int] = None,
        max_timestamp: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return []

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        return None

    def normalize_transaction(self, raw_tx: dict) -> NormalizedTransactionBase:
        raise NotImplementedError()

    async def get_all_token_transfers(
        self,
        address: str,
        token_contract: Optional[str] = None,
        max_pages: int = 5,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        txs = self.topology.get(address, [])
        return {"address": address, "transactions": txs, "total": len(txs), "status": "SUCCESS"}

    def persist_transactions(
        self,
        db: Session,
        transactions: List[NormalizedTransactionBase],
        case_id: Optional[str] = None,
    ) -> int:
        return len(transactions)


@pytest.mark.anyio
async def test_trace_engine_basic_traversal(db: Session):
    """Test basic 2-hop traversal with deterministic mock data."""
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = t0 + timedelta(minutes=10)
    t2 = t1 + timedelta(minutes=15)

    tx1 = NormalizedTransactionBase(
        chain="TRON",
        tx_hash="tx_hash_1",
        block_number=10001,
        timestamp=t1,
        from_address="WALLET_A",
        to_address="WALLET_B",
        asset="USDT",
        amount=1000.0,
        transaction_type="TRANSFER",
        status="SUCCESS",
        source_provider="mock",
        explorer_url="https://tronscan.org/#/transaction/tx_hash_1",
    )

    tx2 = NormalizedTransactionBase(
        chain="TRON",
        tx_hash="tx_hash_2",
        block_number=10002,
        timestamp=t2,
        from_address="WALLET_B",
        to_address="WALLET_C",
        asset="USDT",
        amount=950.0,
        transaction_type="TRANSFER",
        status="SUCCESS",
        source_provider="mock",
        explorer_url="https://tronscan.org/#/transaction/tx_hash_2",
    )

    topology = {
        "WALLET_A": [tx1],
        "WALLET_B": [tx2],
        "WALLET_C": [],
    }

    adapter = MockAdapter(topology=topology)
    engine = TraceEngine(db=db, adapter=adapter)

    request = TraceRequest(
        starting_wallet="WALLET_A",
        chain="TRON",
        asset="USDT",
        max_hops=3,
        min_transfer_amount=10.0,
    )

    result = await engine.execute_trace(request=request)

    assert result.status == "COMPLETED"
    assert result.truncated is False
    assert result.total_wallets_discovered == 3
    assert result.total_edges_discovered == 2
    assert len(result.paths) == 2

    # Verify 2-hop path
    two_hop_paths = [p for p in result.paths if p.hop_count == 2]
    assert len(two_hop_paths) == 1
    path = two_hop_paths[0]
    assert path.wallet_sequence == ["WALLET_A", "WALLET_B", "WALLET_C"]
    assert path.initial_amount == 1000.0
    assert path.final_amount == 950.0
    assert path.value_retention_percent == 95.0
    assert path.cycle_detected is False


@pytest.mark.anyio
async def test_trace_cycle_detection(db: Session):
    """Test cycle detection in circular transfer topology (A -> B -> C -> A)."""
    t0 = datetime.now(timezone.utc) - timedelta(hours=1)
    t1 = t0 + timedelta(minutes=5)
    t2 = t1 + timedelta(minutes=5)
    t3 = t2 + timedelta(minutes=5)

    tx1 = NormalizedTransactionBase(
        chain="TRON",
        tx_hash="cycle_tx_1",
        timestamp=t1,
        from_address="CYCLE_A",
        to_address="CYCLE_B",
        asset="USDT",
        amount=500.0,
        source_provider="mock",
        explorer_url="https://tronscan.org/#/transaction/cycle_tx_1",
    )

    tx2 = NormalizedTransactionBase(
        chain="TRON",
        tx_hash="cycle_tx_2",
        timestamp=t2,
        from_address="CYCLE_B",
        to_address="CYCLE_C",
        asset="USDT",
        amount=480.0,
        source_provider="mock",
        explorer_url="https://tronscan.org/#/transaction/cycle_tx_2",
    )

    tx3 = NormalizedTransactionBase(
        chain="TRON",
        tx_hash="cycle_tx_3",
        timestamp=t3,
        from_address="CYCLE_C",
        to_address="CYCLE_A",  # Back to start
        asset="USDT",
        amount=450.0,
        source_provider="mock",
        explorer_url="https://tronscan.org/#/transaction/cycle_tx_3",
    )

    topology = {
        "CYCLE_A": [tx1],
        "CYCLE_B": [tx2],
        "CYCLE_C": [tx3],
    }

    adapter = MockAdapter(topology=topology)
    engine = TraceEngine(db=db, adapter=adapter)

    request = TraceRequest(
        starting_wallet="CYCLE_A",
        chain="TRON",
        asset="USDT",
        max_hops=5,
    )

    result = await engine.execute_trace(request=request)

    assert result.status == "COMPLETED"
    cycle_paths = [p for p in result.paths if p.cycle_detected]
    assert len(cycle_paths) > 0

    c_path = cycle_paths[0]
    assert c_path.wallet_sequence == ["CYCLE_A", "CYCLE_B", "CYCLE_C", "CYCLE_A"]
    assert c_path.cycle_detected is True
    assert any("Cycle detected" in exp for exp in c_path.relevance_explanation)


@pytest.mark.anyio
async def test_trace_truncation_limits(db: Session):
    """Test that max_total_transactions limit triggers truncation state safely."""
    t0 = datetime.now(timezone.utc)
    txs = []
    for i in range(15):
        txs.append(
            NormalizedTransactionBase(
                chain="TRON",
                tx_hash=f"limit_tx_{i}",
                timestamp=t0 + timedelta(seconds=i),
                from_address="LIMIT_START",
                to_address=f"LIMIT_TARGET_{i}",
                asset="USDT",
                amount=100.0,
                source_provider="mock",
                explorer_url=f"https://tronscan.org/#/transaction/limit_tx_{i}",
            )
        )

    topology = {"LIMIT_START": txs}
    adapter = MockAdapter(topology=topology)
    engine = TraceEngine(db=db, adapter=adapter)

    # Set max_total_transactions to 10 (less than 15 available)
    request = TraceRequest(
        starting_wallet="LIMIT_START",
        chain="TRON",
        asset="USDT",
        max_hops=3,
        max_total_transactions=10,
        max_children_per_node=20,
    )

    result = await engine.execute_trace(request=request)

    assert result.status == "TRUNCATED"
    assert result.truncated is True
    assert "MAX_TOTAL_TRANSACTIONS hard limit" in result.truncation_reason
    assert result.total_transactions_analyzed == 10, "Analyzed transactions must strictly respect the hard limit ceiling without overshoot"


@pytest.mark.anyio
async def test_trace_relevance_scoring_components(db: Session):
    """Verify explainable score components calculation."""
    engine = TraceEngine(db=db, adapter=MockAdapter())

    # High value retention (100%), rapid velocity (120s), high magnitude (50000 USDT), 2 hops
    score, explanations = engine._calculate_relevance_score(
        initial_amount=50000.0,
        final_amount=50000.0,
        value_retention=100.0,
        hop_count=2,
        avg_delta_t=120.0,
        cycle_detected=False,
    )

    # 40 (value) + 30 (temporal <5m) + 20 (mag >=10k) + 10 (hops <=3) = 100
    assert score == 100.0
    assert len(explanations) == 4

    # Test score with cycle penalty
    cycle_score, cycle_exp = engine._calculate_relevance_score(
        initial_amount=50000.0,
        final_amount=50000.0,
        value_retention=100.0,
        hop_count=2,
        avg_delta_t=120.0,
        cycle_detected=True,
    )
    assert cycle_score == 80.0  # 100 * 0.8
    assert any("Cycle detected" in e for e in cycle_exp)


@pytest.mark.anyio
async def test_trace_api_endpoints(client, db: Session):
    """Test API endpoint POST /api/v1/cases/{case_id}/trace and GET retrieval."""
    # Create case first
    case_res = client.post(
        "/api/v1/cases",
        json={
            "investigator_id": "INVESTIGATOR_API_TEST",
            "reported_wallet": "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
            "chain": "TRON",
            "asset": "USDT",
            "description": "API Trace Test Case",
        },
    )
    assert case_res.status_code == 201
    case_id = case_res.json()["case_id"]

    # Execute trace API
    trace_payload = {
        "starting_wallet": "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        "chain": "TRON",
        "asset": "USDT",
        "max_hops": 2,
        "min_transfer_amount": 10.0,
        "max_transactions_per_wallet": 20,
        "max_total_transactions": 50,
    }

    res = client.post(f"/api/v1/cases/{case_id}/trace", json=trace_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == case_id
    assert data["starting_wallet"] == "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"
    assert data["status"] in ["COMPLETED", "TRUNCATED"]
    assert "paths" in data

    trace_id = data["trace_id"]

    # Retrieve trace via GET API
    get_res = client.get(f"/api/v1/cases/{case_id}/traces/{trace_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["trace_id"] == trace_id
    assert get_data["total_wallets_discovered"] == data["total_wallets_discovered"]


@pytest.mark.anyio
async def test_live_tron_multihop_tracing(db: Session):
    """
    Integration Test: Performs multi-hop fund tracing against REAL TRON public blockchain.
    Verifies real downstream hops, real USDT token precision, block_number safety (None/int, no 0),
    and graph persistence.
    """
    adapter = TronAdapter()
    engine = TraceEngine(db=db, adapter=adapter)

    known_active_tron_address = "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"

    request = TraceRequest(
        starting_wallet=known_active_tron_address,
        chain="TRON",
        asset="USDT",
        max_hops=2,
        min_transfer_amount=5.0,
        max_transactions_per_wallet=20,
        max_total_transactions=100,
        max_children_per_node=3,
    )

    result = await engine.execute_trace(request=request)

    assert result.trace_id is not None
    assert result.starting_wallet == known_active_tron_address
    assert result.chain == "TRON"
    assert result.asset == "USDT"
    assert result.status in ["COMPLETED", "TRUNCATED"]
    assert result.total_wallets_discovered >= 1
    assert result.total_transactions_analyzed > 0

    # Verify persistence in database
    db_run = db.query(TraceRun).filter(TraceRun.trace_id == result.trace_id).first()
    assert db_run is not None
    assert db_run.total_transactions_analyzed == result.total_transactions_analyzed

    # If paths were found, verify path metrics and block_number handling
    if result.paths:
        top_path = result.paths[0]
        assert top_path.hop_count >= 1
        assert len(top_path.wallet_sequence) >= 2
        assert top_path.relevance_score >= 0.0
        assert top_path.relevance_score <= 100.0

        for hop in top_path.hops:
            assert hop.tx_hash.startswith("0x") or len(hop.tx_hash) == 64
            assert hop.explorer_url.startswith("https://tronscan.org")
            assert hop.amount > 0.0
            # Ensure block_number is None or positive int (never 0)
            if hop.block_number is not None:
                assert hop.block_number > 0


