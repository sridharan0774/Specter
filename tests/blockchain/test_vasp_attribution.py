import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.models.vasp import VASPRecord, VASPAttribution
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.vasp.repository import VASPRepository
from app.vasp.matcher import VASPMatcher
from app.vasp.scorer import VASPScorer, SCORING_MODEL_VERSION
from app.vasp.evidence import VASPEvidenceBuilder
from app.vasp.service import VASPService


def test_vasp_repository_provenance(db: Session):
    """Test adding entity intelligence record with explicit source provenance."""
    repo = VASPRepository(db)
    record = repo.add_intelligence_record(
        address="TB1234567890BinanceTestWalletAddress",
        chain="TRON",
        entity_name="Binance Test Deposit Wallet",
        entity_type="VASP",
        label_type="deposit_wallet",
        source="Official Exchange Advisory",
        source_url="https://example.com/advisory/123",
        source_reference="ADV-2026-BIN-01",
        source_quality_level=1,
        confidence=0.99,
        notes="Verified official Binance deposit address.",
    )

    assert record.id is not None
    assert record.entity_name == "Binance Test Deposit Wallet"
    assert record.source_quality_level == 1
    assert record.confidence == 0.99
    assert record.source_reference == "ADV-2026-BIN-01"

    found = repo.search_entity("TB1234567890BinanceTestWalletAddress", "TRON")
    assert found is not None
    assert found.entity_name == "Binance Test Deposit Wallet"


def test_vasp_repository_seed(db: Session):
    """Test seeding public documented VASP entity addresses into repository."""
    repo = VASPRepository(db)
    count = repo.seed_known_public_vasps()
    assert count >= 4

    tether = repo.search_entity("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL", "TRON")
    assert tether is not None
    assert tether.entity_name == "Tether Treasury"
    assert tether.source_quality_level == 1


def test_vasp_matcher_find_candidates(db: Session):
    """Test matching known VASP endpoints from a trace path graph."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    matcher = VASPMatcher(repo)

    # Construct synthetic trace response with terminal endpoint matching Binance Deposit Endpoint
    starting_wallet = "TSuspiciousStartingWallet12345678"
    binance_endpoint = "TJCnKsPa7y5okkXvQWBzxaZ2MJK7JBFZ12"

    mock_trace = TraceResultResponse(
        trace_id="test-trace-id-100",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-1",
                wallet_sequence=[starting_wallet, "TIntermediaryRelayWallet1111", binance_endpoint],
                hop_count=2,
                initial_amount=10000.0,
                final_amount=9950.0,
                value_retention_percent=99.5,
                elapsed_time_seconds=300.0,
                relevance_score=95.0,
                relevance_explanation=["High value retention direct flow"],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address="TIntermediaryRelayWallet1111",
                        tx_hash="0xhash111",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                        explorer_url="https://tronscan.org/#/transaction/0xhash111",
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address="TIntermediaryRelayWallet1111",
                        to_address=binance_endpoint,
                        tx_hash="0xhash222",
                        asset="USDT",
                        amount=9950.0,
                        timestamp=datetime.now(timezone.utc),
                        explorer_url="https://tronscan.org/#/transaction/0xhash222",
                    ),
                ],
            )
        ],
    )

    candidates = matcher.find_candidates(mock_trace, starting_wallet)
    assert len(candidates) >= 1

    binance_candidate = next((c for c in candidates if c.candidate_name == "Binance Deposit Endpoint"), None)
    assert binance_candidate is not None
    assert binance_candidate.hop_distance == 2
    assert binance_candidate.attribution_type == "KNOWN_DEPOSIT_ENDPOINT"
    assert binance_candidate.is_terminal_endpoint is True


def test_vasp_scorer_dual_confidence_metrics(db: Session):
    """Test scoring calculation for dual metrics, confidence band, and model versioning."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    matcher = VASPMatcher(repo)
    scorer = VASPScorer()

    starting_wallet = "TSuspiciousWallet999"
    target_hot_wallet = "TND9w8n8n8n8n8n8n8n8n8n8n8n8n8n8n8"

    mock_trace = TraceResultResponse(
        trace_id="test-trace-id-200",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=2,
        total_transactions_analyzed=1,
        total_edges_discovered=1,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-hot",
                wallet_sequence=[starting_wallet, target_hot_wallet],
                hop_count=1,
                initial_amount=50000.0,
                final_amount=50000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=120.0,
                relevance_score=98.0,
                relevance_explanation=["Direct 1-hop hot wallet transfer"],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address=target_hot_wallet,
                        tx_hash="0xhash_direct",
                        asset="USDT",
                        amount=50000.0,
                        timestamp=datetime.now(timezone.utc),
                        explorer_url="https://tronscan.org/#/transaction/0xhash_direct",
                    )
                ],
            )
        ],
    )

    matched = matcher.find_candidates(mock_trace, starting_wallet)
    assert len(matched) == 1

    scored = scorer.score_candidate(matched[0])

    # Check dual confidence metrics
    assert 0.0 <= scored.source_confidence <= 1.0
    assert 80.0 <= scored.attribution_confidence <= 100.0
    assert scored.confidence_band == "HIGH"
    assert "entity_address_match" in scored.score_components
    assert "source_quality_level" in scored.score_components
    assert len(scored.evidence_summary) > 0


def test_negative_result_insufficient_evidence(db: Session):
    """Test that trace with no VASP endpoint matches returns NO HIGH-CONFIDENCE VASP IDENTIFIED."""
    service = VASPService(db)

    starting_wallet = "TUnknownStartingWallet111"
    unknown_terminal = "TUnknownTerminalWallet222"

    mock_trace = TraceResultResponse(
        trace_id="test-trace-negative",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=2,
        total_transactions_analyzed=1,
        total_edges_discovered=1,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-neg",
                wallet_sequence=[starting_wallet, unknown_terminal],
                hop_count=1,
                initial_amount=100.0,
                final_amount=100.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=600.0,
                relevance_score=50.0,
                relevance_explanation=["Flow to unlabelled wallet"],
                hops=[],
            )
        ],
    )

    response = service.resolve_from_trace_result(mock_trace)

    assert response.status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
    assert "NO HIGH-CONFIDENCE VASP IDENTIFIED" in response.explanation
    assert len(response.candidates) == 0
    assert response.scoring_model_version == SCORING_MODEL_VERSION


def test_vasp_attribution_api_endpoints(client: TestClient, db: Session):
    """Integration test for Phase 4 Fast API endpoints."""
    # Create test case
    case = Case(
        investigator_id="inv-p4-test",
        reported_wallet="TSuspiciousStartingWallet12345678",
        chain="TRON",
        asset="USDT",
        description="Phase 4 Integration Test Case",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Seed database trace run & paths
    trace_run = TraceRun(
        trace_id="trace-p4-api-test",
        case_id=case.case_id,
        starting_wallet="TSuspiciousStartingWallet12345678",
        chain="TRON",
        asset="USDT",
        max_hops=2,
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(trace_run)

    trace_path = TracePath(
        trace_id=trace_run.trace_id,
        path_id="path-api-1",
        wallet_sequence=["TSuspiciousStartingWallet12345678", "TND9w8n8n8n8n8n8n8n8n8n8n8n8n8n8n8"],
        edge_sequence=["0xtx_api_1"],
        hop_count=1,
        initial_amount=1000.0,
        final_amount=1000.0,
        value_retention_percent=100.0,
        elapsed_time_seconds=60.0,
        relevance_score=95.0,
        relevance_explanation=["Direct 1-hop hot wallet flow"],
    )
    db.add(trace_path)

    trace_edge = TraceEdge(
        trace_id=trace_run.trace_id,
        from_wallet="TSuspiciousStartingWallet12345678",
        to_wallet="TND9w8n8n8n8n8n8n8n8n8n8n8n8n8n8n8",
        tx_hash="0xtx_api_1",
        asset="USDT",
        amount=1000.0,
        hop=1,
        timestamp=datetime.now(timezone.utc),
        explorer_url="https://tronscan.org/#/transaction/0xtx_api_1",
    )
    db.add(trace_edge)
    db.commit()

    # 1. Test POST /api/v1/cases/{case_id}/vasp-resolve
    res1 = client.post(f"/api/v1/cases/{case.case_id}/vasp-resolve")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "RESOLVED"
    assert data1["scoring_model_version"] == "vasp-score-v1"
    assert len(data1["candidates"]) >= 1

    candidate1 = data1["candidates"][0]
    assert candidate1["candidate_name"] == "Binance Main Exchange Hot Wallet"
    assert candidate1["confidence_band"] == "HIGH"
    assert candidate1["attribution_confidence"] >= 80.0

    # 2. Test GET /api/v1/cases/{case_id}/vasp-candidates
    res2 = client.get(f"/api/v1/cases/{case.case_id}/vasp-candidates")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "RESOLVED"

    # 3. Test POST /api/v1/trace/{trace_id}/vasp-resolve
    res3 = client.post(f"/api/v1/trace/{trace_run.trace_id}/vasp-resolve")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["trace_id"] == trace_run.trace_id
    assert data3["status"] == "RESOLVED"

    # 4. Test GET /api/v1/trace/{trace_id}/vasp-candidates
    res4 = client.get(f"/api/v1/trace/{trace_run.trace_id}/vasp-candidates")
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["trace_id"] == trace_run.trace_id


def test_vasp_source_quality_level5_zero_contribution(db: Session):
    """Test that Level 5 (Unverified) source intelligence contributes 0.0 points to attribution confidence."""
    repo = VASPRepository(db)
    record = repo.add_intelligence_record(
        address="TUnverifiedLevel5Address9999",
        chain="TRON",
        entity_name="Unverified Forum Entity",
        entity_type="VASP",
        label_type="public_address_label",
        source="Random Forum Post",
        source_quality_level=5,
        confidence=0.3,
    )

    matcher = VASPMatcher(repo)
    scorer = VASPScorer()

    starting_wallet = "TSuspiciousWallet111"
    mock_trace = TraceResultResponse(
        trace_id="test-trace-level5",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=2,
        total_transactions_analyzed=1,
        total_edges_discovered=1,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-l5",
                wallet_sequence=[starting_wallet, "TUnverifiedLevel5Address9999"],
                hop_count=1,
                initial_amount=100.0,
                final_amount=100.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=60.0,
                relevance_score=50.0,
                relevance_explanation=[],
                hops=[],
            )
        ],
    )

    matched = matcher.find_candidates(mock_trace, starting_wallet)
    assert len(matched) == 1

    scored = scorer.score_candidate(matched[0])
    assert scored.score_components["source_quality_level"] == 0.0
    assert scored.source_confidence == 0.0

