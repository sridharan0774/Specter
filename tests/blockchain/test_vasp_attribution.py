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


def test_allbridge_and_changenow_seed_audit(db: Session):
    """Verify that Allbridge uses documented router address (non-VASP BRIDGE) and synthetic ChangeNOW address is absent."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    # 1. Documented Allbridge Core Ethereum address is present as BRIDGE
    allbridge = repo.search_entity("0x609c690e8F7D68a59885c9132e812eEbDaAf0c9e", "ETHEREUM")
    assert allbridge is not None
    assert allbridge.entity_name == "Allbridge Core Router"
    assert allbridge.entity_role == "BRIDGE"
    assert allbridge.entity_type == "BRIDGE"
    assert allbridge.is_attributable_vasp is False

    # 2. Synthetic Allbridge and ChangeNOW addresses are absent
    assert repo.search_entity("0x1000000000000000000000000000000000000001") is None
    assert repo.search_entity("0xChangeNOW111111111111111111111111111111") is None



def test_vasp_matcher_find_candidates(db: Session):
    """Test matching known VASP endpoints from a trace path graph."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    matcher = VASPMatcher(repo)

    # Construct synthetic trace response with terminal endpoint matching verified Binance Cold Wallet
    starting_wallet = "TSuspiciousStartingWallet12345678"
    binance_endpoint = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"

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

    binance_candidate = next((c for c in candidates if c.candidate_name == "Binance"), None)
    assert binance_candidate is not None
    assert binance_candidate.hop_distance == 2
    assert binance_candidate.attribution_type == "KNOWN_COLD_WALLET"
    assert binance_candidate.is_terminal_endpoint is True


def test_vasp_scorer_dual_confidence_metrics(db: Session):
    """Test scoring calculation for dual metrics, confidence band, and model versioning."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    matcher = VASPMatcher(repo)
    scorer = VASPScorer()

    starting_wallet = "TSuspiciousWallet999"
    target_hot_wallet = "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76"  # Verified Kraken Hot Wallet

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
    assert scored.candidate_name == "Kraken"
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
        wallet_sequence=["TSuspiciousStartingWallet12345678", "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"],
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
        to_wallet="TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
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
    assert candidate1["candidate_name"] == "Binance"
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


def test_token_contract_is_not_treated_as_vasp(db: Session):
    """
    CRITICAL: Verify that the USDT token contract address (TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t)
    and token issuers (Tether Treasury) are NEVER presented as VASP attribution candidates.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    usdt_contract_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    tether_treasury_addr = "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"

    # 1. Verify entity repository classification
    contract_rec = repo.search_entity(usdt_contract_addr, "TRON")
    assert contract_rec is not None
    assert contract_rec.entity_role == "TOKEN_CONTRACT"
    assert contract_rec.is_attributable_vasp is False

    treasury_rec = repo.search_entity(tether_treasury_addr, "TRON")
    assert treasury_rec is not None
    assert treasury_rec.entity_role == "TOKEN_ISSUER"
    assert treasury_rec.is_attributable_vasp is False

    # 2. Test that matcher refuses to treat token contract or issuer as candidate
    matcher = VASPMatcher(repo)
    starting_wallet = "TSuspiciousWallet111"

    trace_to_contract = TraceResultResponse(
        trace_id="trace-contract-test",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=2,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-to-contract",
                wallet_sequence=[starting_wallet, usdt_contract_addr],
                hop_count=1,
                initial_amount=1000.0,
                final_amount=1000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=60.0,
                relevance_score=50.0,
                relevance_explanation=[],
                hops=[],
            ),
            TracePathDetail(
                path_id="path-to-treasury",
                wallet_sequence=[starting_wallet, tether_treasury_addr],
                hop_count=1,
                initial_amount=5000.0,
                final_amount=5000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=120.0,
                relevance_score=50.0,
                relevance_explanation=[],
                hops=[],
            ),
        ],
    )

    candidates = matcher.find_candidates(trace_to_contract, starting_wallet)
    assert len(candidates) == 0, "USDT token contract and token issuer must never be matched as VASP candidates"

    # 3. Test that service returns NO_HIGH_CONFIDENCE_VASP_IDENTIFIED
    service = VASPService(db)
    response = service.resolve_from_trace_result(trace_to_contract)
    assert response.status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
    assert len(response.candidates) == 0


def test_terminal_endpoint_vs_intermediate_association(db: Session):
    """
    Test that the attribution engine strictly distinguishes between:
    - DIRECT / TERMINAL ENDPOINT (funds arrive and terminate at VASP)
    - INTERMEDIATE ASSOCIATION (funds pass through known wallet to further addresses)
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    starting_wallet = "TSuspiciousStarting111"
    binance_wallet = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
    unclassified_terminal = "TUnclassifiedTerminal999"

    # Trace A: Terminal match (funds terminate at Binance Wallet)
    trace_terminal = TraceResultResponse(
        trace_id="trace-terminal-test",
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
                path_id="path-terminal",
                wallet_sequence=[starting_wallet, "TRelayWallet1", binance_wallet],
                hop_count=2,
                initial_amount=10000.0,
                final_amount=9900.0,
                value_retention_percent=99.0,
                elapsed_time_seconds=180.0,
                relevance_score=95.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address="TRelayWallet1",
                        tx_hash="0xtx1",
                        explorer_url="https://tronscan.org/#/transaction/0xtx1",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address="TRelayWallet1",
                        to_address=binance_wallet,
                        tx_hash="0xtx2",
                        explorer_url="https://tronscan.org/#/transaction/0xtx2",
                        asset="USDT",
                        amount=9900.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            )
        ],
    )

    resp_terminal = service.resolve_from_trace_result(trace_terminal)
    assert resp_terminal.status == "RESOLVED"
    assert len(resp_terminal.candidates) == 1
    cand_term = resp_terminal.candidates[0]
    assert cand_term.candidate_name == "Binance"
    assert cand_term.is_terminal_endpoint is True
    assert cand_term.match_position == "TERMINAL_ENDPOINT"
    assert cand_term.attribution_type == "KNOWN_COLD_WALLET"
    assert cand_term.attribution_confidence >= 80.0

    # Trace B: Intermediate match (funds merely pass through Binance Wallet to an unclassified wallet)
    trace_intermediate = TraceResultResponse(
        trace_id="trace-intermediate-test",
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
                path_id="path-intermediate",
                wallet_sequence=[starting_wallet, binance_wallet, unclassified_terminal],
                hop_count=2,
                initial_amount=10000.0,
                final_amount=9500.0,
                value_retention_percent=95.0,
                elapsed_time_seconds=300.0,
                relevance_score=70.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address=binance_wallet,
                        tx_hash="0xtx3",
                        explorer_url="https://tronscan.org/#/transaction/0xtx3",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address=binance_wallet,
                        to_address=unclassified_terminal,
                        tx_hash="0xtx4",
                        explorer_url="https://tronscan.org/#/transaction/0xtx4",
                        asset="USDT",
                        amount=9500.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            )
        ],
    )

    resp_intermediate = service.resolve_from_trace_result(trace_intermediate)
    # Must NOT be resolved as a high-confidence VASP endpoint because it was only an intermediate pass-through!
    assert resp_intermediate.status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
    assert len(resp_intermediate.candidates) == 1
    cand_inter = resp_intermediate.candidates[0]
    assert cand_inter.is_terminal_endpoint is False
    assert cand_inter.match_position == "INTERMEDIATE_ASSOCIATION"
    assert cand_inter.attribution_type == "INTERMEDIATE_ASSOCIATION"
    # Intermediate association receives significantly penalized score compared to terminal endpoint
    assert cand_inter.attribution_confidence < cand_term.attribution_confidence
    assert resp_intermediate.negative_reason is not None
    assert "intermediate hop" in resp_intermediate.negative_reason


def test_hop_distance_scoring_and_candidate_ranking(db: Session):
    """
    Test that nearer terminal endpoints receive higher proximity score and rank higher.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    starting_wallet = "TSuspiciousMultiPath1"
    binance_wallet = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"  # 1 hop (Binance)
    okx_wallet = "TLaGjwhvA8XQYSxFAcAXy7Dvuue9eGYitv"      # 3 hops (OKX Hot Wallet 8)

    trace_multi = TraceResultResponse(
        trace_id="trace-multi-ranking",
        starting_wallet=starting_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=5,
        total_transactions_analyzed=4,
        total_edges_discovered=4,
        total_paths_found=2,
        started_at=datetime.now(timezone.utc),
        paths=[
            # Path 1: 1 hop to Binance Cold Wallet
            TracePathDetail(
                path_id="path-binance-1hop",
                wallet_sequence=[starting_wallet, binance_wallet],
                hop_count=1,
                initial_amount=20000.0,
                final_amount=20000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=60.0,
                relevance_score=98.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address=binance_wallet,
                        tx_hash="0xtx_b1",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_b1",
                        asset="USDT",
                        amount=20000.0,
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
            ),
            # Path 2: 3 hops to OKX
            TracePathDetail(
                path_id="path-okx-3hop",
                wallet_sequence=[starting_wallet, "TRelayX", "TRelayY", okx_wallet],
                hop_count=3,
                initial_amount=10000.0,
                final_amount=9500.0,
                value_retention_percent=95.0,
                elapsed_time_seconds=1200.0,
                relevance_score=85.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address="TRelayX",
                        tx_hash="0xtx_o1",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_o1",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address="TRelayX",
                        to_address="TRelayY",
                        tx_hash="0xtx_o2",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_o2",
                        asset="USDT",
                        amount=9800.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=3,
                        from_address="TRelayY",
                        to_address=okx_wallet,
                        tx_hash="0xtx_o3",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_o3",
                        asset="USDT",
                        amount=9500.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace_multi)
    assert resp.status == "RESOLVED"
    assert len(resp.candidates) == 2

    # Rank 1 must be Binance (1 hop away, higher score)
    top = resp.candidates[0]
    assert top.candidate_name == "Binance"
    assert top.endpoint_hop_distance == 1
    assert top.rank == 1

    # Rank 2 must be OKX (3 hops away)
    second = resp.candidates[1]
    assert second.candidate_name == "OKX"
    assert second.endpoint_hop_distance == 3
    assert second.rank == 2

    assert top.attribution_confidence > second.attribution_confidence


def test_why_this_vasp_explainability_and_provenance(db: Session):
    """
    Test that attribution outputs concise, factual 'WHY THIS VASP?' evidence items
    grounded strictly in trace path data and intelligence source provenance.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    starting_wallet = "TSuspiciousExplain123"
    target_wallet = "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76"  # Verified Kraken Hot Wallet

    mock_trace = TraceResultResponse(
        trace_id="trace-explain-test",
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
                path_id="path-kraken",
                wallet_sequence=[starting_wallet, target_wallet],
                hop_count=1,
                initial_amount=15000.0,
                final_amount=15000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=45.0,
                relevance_score=98.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address=target_wallet,
                        tx_hash="0xtx_kraken",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_kraken",
                        asset="USDT",
                        amount=15000.0,
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
            )
        ],
    )

    resp = service.resolve_from_trace_result(mock_trace)
    assert resp.status == "RESOLVED"
    cand = resp.candidates[0]
    assert cand.candidate_name == "Kraken"

    # Verify explainable why_this_vasp evidence items
    assert cand.why_this_vasp is not None
    assert len(cand.why_this_vasp) >= 5

    reasons_text = " ".join(cand.why_this_vasp)
    assert "terminal traced endpoint" in reasons_text
    assert "1 hop(s) distance" in reasons_text
    assert "100.0% of traced value reaches the endpoint" in reasons_text
    assert "Transaction timing is consistent with rapid movement based on observed transaction timestamps" in reasons_text
    assert "Level 2 provenance" in reasons_text

    # Verify provenance metadata
    assert cand.source_metadata["source"] == "TRONSCAN Public Entity Labels"
    assert cand.source_metadata["source_reference"] == "TRONSCAN-LABEL-KRAKEN-HOT-01"
    assert cand.source_metadata["source_quality_level"] == 2


def test_candidate_ranking_terminal_over_intermediate(db: Session):
    """
    Test that terminal endpoints are strictly prioritized over intermediate associations
    even if the intermediate association was 1 hop and terminal was 2 hops.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    starting_wallet = "TInvestigateWallet555"
    bybit_intermediate = "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"  # 1 hop intermediate (Verified Bybit Hot Wallet)
    kraken_terminal = "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76"     # 2 hops terminal endpoint (Verified Kraken Hot Wallet)

    mock_trace = TraceResultResponse(
        trace_id="trace-ranking-terminal-over-intermediate",
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
                path_id="path-thru-bybit-to-kraken",
                wallet_sequence=[starting_wallet, bybit_intermediate, kraken_terminal],
                hop_count=2,
                initial_amount=10000.0,
                final_amount=9900.0,
                value_retention_percent=99.0,
                elapsed_time_seconds=120.0,
                relevance_score=92.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=starting_wallet,
                        to_address=bybit_intermediate,
                        tx_hash="0xtx_byb",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_byb",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address=bybit_intermediate,
                        to_address=kraken_terminal,
                        tx_hash="0xtx_krk",
                        explorer_url="https://tronscan.org/#/transaction/0xtx_krk",
                        asset="USDT",
                        amount=9900.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            )
        ],
    )

    resp = service.resolve_from_trace_result(mock_trace)
    assert resp.status == "RESOLVED"
    assert len(resp.candidates) == 2

    # Kraken is the terminal endpoint -> MUST be Rank 1!
    rank1 = resp.candidates[0]
    assert rank1.candidate_name == "Kraken"
    assert rank1.is_terminal_endpoint is True
    assert rank1.match_position == "TERMINAL_ENDPOINT"
    assert rank1.rank == 1

    # Bybit was merely an intermediate relay -> Rank 2
    rank2 = resp.candidates[1]
    assert rank2.candidate_name == "Bybit"
    assert rank2.is_terminal_endpoint is False
    assert rank2.match_position == "INTERMEDIATE_ASSOCIATION"
    assert rank2.rank == 2


def test_controlled_sih_suspicious_to_intermediate_to_verified_vasp(db: Session):
    """
    Controlled SIH Test:
    Suspicious Wallet -> Intermediate Wallet -> Verified VASP Wallet (Binance Cold)
    Verify returns: Likely VASP, terminal endpoint, hop distance, confidence, provenance, WHY THIS VASP evidence.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    suspicious_wallet = "TSuspiciousOriginWallet98765"
    intermediate_wallet = "TRelayIntermediateMule12345"
    verified_vasp_wallet = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"  # Verified Binance Cold/Reserve

    trace = TraceResultResponse(
        trace_id="trace-sih-controlled-01",
        starting_wallet=suspicious_wallet,
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
                path_id="path-sih-terminal",
                wallet_sequence=[suspicious_wallet, intermediate_wallet, verified_vasp_wallet],
                hop_count=2,
                initial_amount=25000.0,
                final_amount=24800.0,
                value_retention_percent=99.2,
                elapsed_time_seconds=180.0,
                relevance_score=96.0,
                relevance_explanation=["Direct layered flow into verified custodial endpoint"],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=suspicious_wallet,
                        to_address=intermediate_wallet,
                        tx_hash="0xsih_tx_1",
                        explorer_url="https://tronscan.org/#/transaction/0xsih_tx_1",
                        asset="USDT",
                        amount=25000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address=intermediate_wallet,
                        to_address=verified_vasp_wallet,
                        tx_hash="0xsih_tx_2",
                        explorer_url="https://tronscan.org/#/transaction/0xsih_tx_2",
                        asset="USDT",
                        amount=24800.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            )
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert resp.status == "RESOLVED"
    assert len(resp.candidates) == 1

    top = resp.candidates[0]
    assert top.candidate_name == "Binance"
    assert top.is_terminal_endpoint is True
    assert top.match_position == "TERMINAL_ENDPOINT"
    assert top.endpoint_hop_distance == 2
    assert top.attribution_confidence >= 80.0
    assert top.confidence_band == "HIGH"
    assert top.source_metadata["source_quality_level"] == 1
    assert "Proof of Reserves" in top.source_metadata["source"]
    assert top.source_metadata["source_reference"] == "BINANCE-POR-TRON-COLD-01"

    # Factual explainability points
    assert top.why_this_vasp is not None
    assert len(top.why_this_vasp) >= 5
    why_text = " ".join(top.why_this_vasp)
    assert "terminal traced endpoint" in why_text
    assert "2 hop(s) distance" in why_text
    assert "Level 1 provenance" in why_text


def test_controlled_sih_suspicious_through_vasp_to_unknown(db: Session):
    """
    Controlled SIH Test:
    Suspicious Wallet -> Verified VASP -> Unknown Wallet
    The VASP must be classified as INTERMEDIATE_ASSOCIATION and must NOT automatically
    become a high-confidence terminal attribution.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    suspicious_wallet = "TSuspiciousOriginWallet555"
    verified_vasp_wallet = "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76"  # Verified Kraken Hot Wallet
    unknown_wallet = "TUnknownDestinationWallet999"

    trace = TraceResultResponse(
        trace_id="trace-sih-controlled-02",
        starting_wallet=suspicious_wallet,
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
                path_id="path-sih-pass-through",
                wallet_sequence=[suspicious_wallet, verified_vasp_wallet, unknown_wallet],
                hop_count=2,
                initial_amount=10000.0,
                final_amount=9500.0,
                value_retention_percent=95.0,
                elapsed_time_seconds=300.0,
                relevance_score=75.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address=suspicious_wallet,
                        to_address=verified_vasp_wallet,
                        tx_hash="0xsih_tx_3",
                        explorer_url="https://tronscan.org/#/transaction/0xsih_tx_3",
                        asset="USDT",
                        amount=10000.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                    TraceHopItem(
                        hop_number=2,
                        from_address=verified_vasp_wallet,
                        to_address=unknown_wallet,
                        tx_hash="0xsih_tx_4",
                        explorer_url="https://tronscan.org/#/transaction/0xsih_tx_4",
                        asset="USDT",
                        amount=9500.0,
                        timestamp=datetime.now(timezone.utc),
                    ),
                ],
            )
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert resp.status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
    assert len(resp.candidates) == 1

    cand = resp.candidates[0]
    assert cand.candidate_name == "Kraken"
    assert cand.is_terminal_endpoint is False
    assert cand.match_position == "INTERMEDIATE_ASSOCIATION"
    assert cand.attribution_type == "INTERMEDIATE_ASSOCIATION"
    assert resp.negative_reason is not None
    assert "intermediate hop" in resp.negative_reason


def test_controlled_non_vasp_entities_excluded(db: Session):
    """
    Controlled Test:
    Verify that Tether Treasury and USDT Smart Contract are recognized with their respective roles
    (TOKEN_ISSUER and TOKEN_CONTRACT), and are NEVER attributed as VASPs.
    """
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    # 1. Verify entity repository classification
    treasury_rec = repo.search_entity("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL", "TRON")
    assert treasury_rec is not None
    assert treasury_rec.entity_role == "TOKEN_ISSUER"
    assert treasury_rec.is_attributable_vasp is False

    contract_rec = repo.search_entity("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "TRON")
    assert contract_rec is not None
    assert contract_rec.entity_role == "TOKEN_CONTRACT"
    assert contract_rec.is_attributable_vasp is False

    # 2. Verify in trace evaluation
    suspicious_wallet = "TSuspiciousOriginWallet111"
    trace = TraceResultResponse(
        trace_id="trace-non-vasp-test",
        starting_wallet=suspicious_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=2,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-contract",
                wallet_sequence=[suspicious_wallet, "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"],
                hop_count=1,
                initial_amount=1000.0,
                final_amount=1000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=60.0,
                relevance_score=50.0,
                relevance_explanation=[],
                hops=[],
            ),
            TracePathDetail(
                path_id="path-treasury",
                wallet_sequence=[suspicious_wallet, "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL"],
                hop_count=1,
                initial_amount=5000.0,
                final_amount=5000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=120.0,
                relevance_score=50.0,
                relevance_explanation=[],
                hops=[],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert resp.status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
    assert len(resp.candidates) == 0
    assert resp.negative_reason is not None


def test_evidence_audit_timestamp_precision(db: Session):
    """Audit #1: Ensure timing explanation never claims '0 seconds' and uses factual wording."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    # 1-hop path with 0 elapsed seconds
    trace_1hop = TraceResultResponse(
        trace_id="trace-timing-1hop",
        starting_wallet="TSuspiciousOrigin999",
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
                path_id="path-1hop-1",
                wallet_sequence=["TSuspiciousOrigin999", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=1,
                initial_amount=100.0,
                final_amount=100.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=0.0,
                relevance_score=80.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address="TSuspiciousOrigin999",
                        to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY",
                        tx_hash="txhash_1hop_1",
                        asset="USDT",
                        amount=100.0,
                        timestamp=datetime.now(timezone.utc),
                        explorer_url="https://tronscan.org/#/transaction/txhash_1hop_1",
                    ),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace_1hop)
    assert resp.status == "RESOLVED"
    cand = resp.candidates[0]
    # Verify no fabricated 'within 0 seconds' in why_this_vasp or evidence statements
    for item in cand.why_this_vasp:
        assert "within 0 seconds" not in item
        assert "within 0.0 seconds" not in item
    assert any("consistent with rapid movement based on observed transaction timestamps" in item for item in cand.why_this_vasp)


def test_evidence_audit_convergence_calculation(db: Session):
    """Audit #2: Verify path convergence deduplication and removal of unverified 'independent' claim."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    # 3 distinct paths converging on Bybit
    trace = TraceResultResponse(
        trace_id="trace-convergence-audit",
        starting_wallet="TSuspiciousOrigin999",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=5,
        total_transactions_analyzed=5,
        total_edges_discovered=5,
        total_paths_found=3,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-conv-1",
                wallet_sequence=["TSuspiciousOrigin999", "TIntermediary1", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=2,
                initial_amount=100.0,
                final_amount=50.0,
                value_retention_percent=50.0,
                elapsed_time_seconds=60.0,
                relevance_score=80.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TIntermediary1", tx_hash="tx_c1", asset="USDT", amount=100.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TIntermediary1", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_c2", asset="USDT", amount=50.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
            TracePathDetail(
                path_id="path-conv-2",
                wallet_sequence=["TSuspiciousOrigin999", "TIntermediary2", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=2,
                initial_amount=100.0,
                final_amount=40.0,
                value_retention_percent=40.0,
                elapsed_time_seconds=90.0,
                relevance_score=75.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TIntermediary2", tx_hash="tx_c3", asset="USDT", amount=100.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TIntermediary2", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_c4", asset="USDT", amount=40.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
            # Duplicate path submission with same path_id
            TracePathDetail(
                path_id="path-conv-2",
                wallet_sequence=["TSuspiciousOrigin999", "TIntermediary2", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=2,
                initial_amount=100.0,
                final_amount=40.0,
                value_retention_percent=40.0,
                elapsed_time_seconds=90.0,
                relevance_score=75.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TIntermediary2", tx_hash="tx_c3", asset="USDT", amount=100.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TIntermediary2", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_c4", asset="USDT", amount=40.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert resp.status == "RESOLVED"
    cand = resp.candidates[0]
    # Path convergence count must deduplicate path-conv-2 (should be exactly 2 distinct paths)
    assert cand.path_convergence_count == 2
    # Verify unverified word 'independent' is NOT used
    for item in cand.why_this_vasp:
        assert "independent" not in item.lower()
    assert any("2 traced paths converge on this entity" in item for item in cand.why_this_vasp)


def test_evidence_audit_value_retention(db: Session):
    """Audit #3: Verify multi-branch value aggregation without double-counting."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    # 2 branches splitting from origin: 400 USDT and 600 USDT into Bybit
    trace = TraceResultResponse(
        trace_id="trace-retention-audit",
        starting_wallet="TSuspiciousOrigin999",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=4,
        total_transactions_analyzed=4,
        total_edges_discovered=4,
        total_paths_found=2,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-split-1",
                wallet_sequence=["TSuspiciousOrigin999", "TBranch1", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=2,
                initial_amount=1000.0,
                final_amount=400.0,
                value_retention_percent=40.0,
                elapsed_time_seconds=100.0,
                relevance_score=80.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TBranch1", tx_hash="tx_split_1", asset="USDT", amount=400.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TBranch1", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_split_2", asset="USDT", amount=400.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
            TracePathDetail(
                path_id="path-split-2",
                wallet_sequence=["TSuspiciousOrigin999", "TBranch2", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=2,
                initial_amount=1000.0,
                final_amount=600.0,
                value_retention_percent=60.0,
                elapsed_time_seconds=120.0,
                relevance_score=85.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TBranch2", tx_hash="tx_split_3", asset="USDT", amount=600.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TBranch2", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_split_4", asset="USDT", amount=600.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert resp.status == "RESOLVED"
    cand = resp.candidates[0]
    # Sum of unique incoming transfers: 400 + 600 = 1000.0 USDT
    assert cand.value_transferred == 1000.0


def test_evidence_audit_supporting_transaction_count(db: Session):
    """Audit #4: Verify supporting transactions only include txs leading to the candidate, strictly excluding downstream txs."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    # 3-hop path where Bybit is at Hop 1, followed by 2 downstream hops
    trace = TraceResultResponse(
        trace_id="trace-supporting-tx-audit",
        starting_wallet="TSuspiciousOrigin999",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=4,
        total_transactions_analyzed=3,
        total_edges_discovered=3,
        total_paths_found=1,
        started_at=datetime.now(timezone.utc),
        paths=[
            TracePathDetail(
                path_id="path-3hops-with-bybit-first",
                wallet_sequence=["TSuspiciousOrigin999", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", "TDownstream1", "TDownstream2"],
                hop_count=3,
                initial_amount=500.0,
                final_amount=500.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=300.0,
                relevance_score=70.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_leading_1", asset="USDT", amount=500.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=2, from_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", to_address="TDownstream1", tx_hash="tx_downstream_2", asset="USDT", amount=500.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                    TraceHopItem(hop_number=3, from_address="TDownstream1", to_address="TDownstream2", tx_hash="tx_downstream_3", asset="USDT", amount=500.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    assert len(resp.candidates) == 1
    cand = resp.candidates[0]
    # Bybit was matched at hop 1. Supporting transactions MUST only be ['tx_leading_1'], NOT downstream txs!
    assert cand.supporting_transactions == ["tx_leading_1"]
    assert len(cand.supporting_transactions) == 1


def test_evidence_audit_score_component_sum(db: Session):
    """Audit #5: Verify that the final attribution score exactly equals the sum of all displayed score components."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()
    service = VASPService(db)

    trace = TraceResultResponse(
        trace_id="trace-score-sum-audit",
        starting_wallet="TSuspiciousOrigin999",
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
                path_id="path-sum-1",
                wallet_sequence=["TSuspiciousOrigin999", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY"],
                hop_count=1,
                initial_amount=100.0,
                final_amount=100.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=0.0,
                relevance_score=80.0,
                relevance_explanation=[],
                hops=[
                    TraceHopItem(hop_number=1, from_address="TSuspiciousOrigin999", to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", tx_hash="tx_sum_1", asset="USDT", amount=100.0, timestamp=datetime.now(timezone.utc), explorer_url=""),
                ],
            ),
        ],
    )

    resp = service.resolve_from_trace_result(trace)
    cand = resp.candidates[0]
    assert len(cand.score_components) == 7
    expected_sum = sum(cand.score_components.values())
    assert round(expected_sum, 2) == round(cand.attribution_confidence, 2)


def test_evidence_audit_provenance_linkage(db: Session):
    """Audit #6: Verify that Bybit Level 1 record points directly to official documentation URL."""
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    rec = repo.search_entity("TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", "TRON")
    assert rec is not None
    assert rec.source_quality_level == 1
    assert rec.source == "Bybit Official Wallet Address Ownership Documentation"
    assert rec.source_url == "https://www.bybit.com/en/help-center/s/article/Bybit-Wallet-Addresses-Ownership-Explained"
    assert rec.source_reference == "BYBIT-OFFICIAL-OWNERSHIP-TRON-02"
