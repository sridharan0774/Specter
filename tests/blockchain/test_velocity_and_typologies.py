import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.models.vasp import VASPRecord
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.velocity.detector import VelocityDetector
from app.velocity.scorer import VelocityScorer
from app.velocity.service import VelocityService
from app.typologies.detector import TypologyDetector
from app.typologies.scorer import TypologyScorer
from app.typologies.service import TypologyService
from app.risk.scorer import RiskScorer
from app.risk.service import RiskService
from app.vasp.repository import VASPRepository
from app.vasp.service import VASPService



def create_sample_trace_response() -> TraceResultResponse:
    """Helper to generate a mock multi-hop TraceResultResponse for unit testing."""
    now = datetime.now(timezone.utc)
    t1 = now.isoformat()
    t2 = datetime.fromtimestamp(now.timestamp() + 30.0, timezone.utc).isoformat()
    t3 = datetime.fromtimestamp(now.timestamp() + 90.0, timezone.utc).isoformat()

    h1_hash = "0xhash111111111111111111111111111111111111111111111111111111111111"
    h2_hash = "0xhash222222222222222222222222222222222222222222222222222222222222"
    h3_hash = "0xhash333333333333333333333333333333333333333333333333333333333333"

    hop1 = TraceHopItem(
        hop_number=1,
        from_address="TStartingWallet111111111111111111111",
        to_address="THopWallet111111111111111111111111",
        tx_hash=h1_hash,
        asset="USDT",
        amount=50000.0,
        timestamp=t1,
        delta_t_seconds=0.0,
        explorer_url=f"https://tronscan.org/#/transaction/{h1_hash}",
    )

    hop2 = TraceHopItem(
        hop_number=2,
        from_address="THopWallet111111111111111111111111",
        to_address="THopWallet222222222222222222222222",
        tx_hash=h2_hash,
        asset="USDT",
        amount=48000.0,
        timestamp=t2,
        delta_t_seconds=30.0,
        explorer_url=f"https://tronscan.org/#/transaction/{h2_hash}",
    )

    hop3 = TraceHopItem(
        hop_number=3,
        from_address="THopWallet222222222222222222222222",
        to_address="THopWallet333333333333333333333333",
        tx_hash=h3_hash,
        asset="USDT",
        amount=47000.0,
        timestamp=t3,
        delta_t_seconds=60.0,
        explorer_url=f"https://tronscan.org/#/transaction/{h3_hash}",
    )

    path1 = TracePathDetail(
        path_id="path-001",
        wallet_sequence=[
            "TStartingWallet111111111111111111111",
            "THopWallet111111111111111111111111",
            "THopWallet222222222222222222222222",
            "THopWallet333333333333333333333333",
        ],
        hop_count=3,
        initial_amount=50000.0,
        final_amount=47000.0,
        value_retention_percent=94.0,
        elapsed_time_seconds=90.0,
        relevance_score=95.0,
        relevance_explanation=["High value retention rapid multi-hop path."],
        hops=[hop1, hop2, hop3],
    )

    return TraceResultResponse(
        trace_id="tr-test-velocity-001",
        case_id="case-test-001",
        starting_wallet="TStartingWallet111111111111111111111",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=4,
        total_transactions_analyzed=3,
        total_edges_discovered=3,
        total_paths_found=1,
        started_at=now,
        completed_at=now,
        paths=[path1],
    )


def test_velocity_detector_metrics():
    """Test calculation of delta_t, rolling windows, and summary metrics."""
    detector = VelocityDetector()
    trace_res = create_sample_trace_response()

    metrics = detector.analyze_trace_velocity(trace_res)

    assert metrics.transfer_count == 3
    assert metrics.total_amount == 145000.0
    assert metrics.duration_seconds == 90.0
    assert metrics.minimum_delta_t == 30.0
    assert metrics.average_delta_t == 45.0
    assert metrics.maximum_delta_t == 60.0
    assert metrics.unique_recipients == 3
    assert metrics.downstream_hops == 3

    # Check rolling windows
    assert "1m" in metrics.rolling_windows
    assert "5m" in metrics.rolling_windows
    assert "10m" in metrics.rolling_windows
    assert "30m" in metrics.rolling_windows
    assert "1h" in metrics.rolling_windows

    win_5m = metrics.rolling_windows["5m"]
    assert win_5m.transfer_count == 3
    assert win_5m.total_amount == 145000.0


def test_velocity_scorer():
    """Test calculation of Velocity Alert Score (0-100), severity, and reason codes."""
    scorer = VelocityScorer()
    detector = VelocityDetector()
    trace_res = create_sample_trace_response()
    metrics = detector.analyze_trace_velocity(trace_res)

    score, severity, reason_codes, components = scorer.score_velocity(metrics)

    assert score > 50.0
    assert severity in ["HIGH", "CRITICAL"]
    assert "RAPID_SUCCESSIVE_TRANSFERS" in reason_codes
    assert "HIGH_VALUE_RAPID_MOVEMENT" in reason_codes
    assert "transfer_frequency" in components
    assert "minimum_delta_t" in components


def test_typology_detector_rules():
    """Test Fan-Out, Fan-In, Consolidation, and Rapid Peel rules."""
    detector = TypologyDetector()
    trace_res = create_sample_trace_response()

    results = detector.analyze_typologies(trace_res)
    typ_names = [t.typology_name for t in results]

    assert "RAPID_PEEL_LIKE_MOVEMENT" in typ_names

    peel_typ = next(t for t in results if t.typology_name == "RAPID_PEEL_LIKE_MOVEMENT")
    assert peel_typ.severity in ["HIGH", "MODERATE"]
    assert peel_typ.metrics["hop_count"] == 3
    assert peel_typ.metrics["value_retention_percent"] == 94.0


def test_risk_indicator_and_false_positive_mitigation(db: Session):
    """Test Transaction-Flow Risk Indicator scoring and false-positive safety mitigation."""
    # Seed a known exchange VASP record in DB
    vasp_repo = VASPRepository(db)
    vasp_repo.add_intelligence_record(
        address="THopWallet333333333333333333333333",
        chain="TRON",
        entity_name="Huobi Exchange Deposit Wallet",
        entity_type="VASP",
        label_type="deposit_wallet",
        source="Official Exchange Directory",
        source_quality_level=1,
        confidence=0.98,
    )

    trace_res = create_sample_trace_response()
    vasp_service = VASPService(db)
    vasp_resp = vasp_service.resolve_from_trace_result(trace_res)

    risk_service = RiskService(db)
    risk_resp = risk_service.analyze_trace(trace_res, vasp_resp=vasp_resp)

    assert risk_resp.risk_score <= 50.0  # Contextual score evaluated with VASP context
    assert risk_resp.is_known_service_entity is True
    assert risk_resp.service_entity_context is True

    assert "VASP" in risk_resp.false_positive_mitigations[0] or "exchange" in risk_resp.false_positive_mitigations[0]



def test_velocity_and_typology_api_endpoints(client: TestClient, db: Session):
    """Integration test for Phase 5 API endpoints."""
    # Create Case record
    c = Case(
        case_id="case-api-test-001",
        investigator_id="INV-TEST-001",
        reported_wallet="TTestApiWallet111111111111111111111",
        chain="TRON",
        asset="USDT",
        description="APIs Test Case",
    )
    db.add(c)

    # Create TraceRun record
    tr = TraceRun(
        trace_id="tr-api-test-001",
        case_id="case-api-test-001",
        starting_wallet="TTestApiWallet111111111111111111111",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
    )
    db.add(tr)

    path = TracePath(
        path_id="p-api-001",
        trace_id="tr-api-test-001",
        wallet_sequence=[
            "TTestApiWallet111111111111111111111",
            "TTestApiWallet222222222222222222222",
            "TTestApiWallet333333333333333333333",
        ],
        hop_count=2,
        initial_amount=10000.0,
        final_amount=9500.0,
        value_retention_percent=95.0,
        elapsed_time_seconds=120.0,
        relevance_score=95.0,
        relevance_explanation=["High relevance path"],
        edge_sequence=["tx-api-001", "tx-api-002"],
    )
    db.add(path)

    edge1 = TraceEdge(
        tx_hash="tx-api-001",
        trace_id="tr-api-test-001",
        from_wallet="TTestApiWallet111111111111111111111",
        to_wallet="TTestApiWallet222222222222222222222",
        amount=10000.0,
        asset="USDT",
        timestamp=datetime.now(timezone.utc),
        delta_t_seconds=0.0,
        hop=1,
        explorer_url="https://tronscan.org/#/transaction/tx-api-001",
    )
    edge2 = TraceEdge(
        tx_hash="tx-api-002",
        trace_id="tr-api-test-001",
        from_wallet="TTestApiWallet222222222222222222222",
        to_wallet="TTestApiWallet333333333333333333333",
        amount=9500.0,
        asset="USDT",
        timestamp=datetime.now(timezone.utc),
        delta_t_seconds=120.0,
        hop=2,
        explorer_url="https://tronscan.org/#/transaction/tx-api-002",
    )
    db.add(edge1)
    db.add(edge2)
    db.commit()

    # 1. POST /api/v1/cases/{case_id}/velocity-analyze
    resp1 = client.post(f"/api/v1/cases/case-api-test-001/velocity-analyze")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["trace_id"] == "tr-api-test-001"
    assert "metrics" in data1

    # 2. GET /api/v1/cases/{case_id}/velocity-alerts
    resp2 = client.get(f"/api/v1/cases/case-api-test-001/velocity-alerts")
    assert resp2.status_code == 200

    # 3. GET /api/v1/cases/{case_id}/typologies
    resp3 = client.get(f"/api/v1/cases/case-api-test-001/typologies")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["trace_id"] == "tr-api-test-001"
    assert "typologies" in data3

    # 4. GET /api/v1/cases/{case_id}/risk
    resp4 = client.get(f"/api/v1/cases/case-api-test-001/risk")
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert "risk_score" in data4
    assert "risk_level" in data4

    # 5. POST /api/v1/trace/{trace_id}/analyze-patterns
    resp5 = client.post(f"/api/v1/trace/tr-api-test-001/analyze-patterns")
    assert resp5.status_code == 200
    data5 = resp5.json()
    assert "velocity_analysis" in data5
    assert "typology_analysis" in data5
    assert "risk_indicator" in data5

    # 6. GET /api/v1/trace/{trace_id}/alerts
    resp6 = client.get(f"/api/v1/trace/tr-api-test-001/alerts")
    assert resp6.status_code == 200

    # 7. GET /api/v1/trace/{trace_id}/typologies
    resp7 = client.get(f"/api/v1/trace/tr-api-test-001/typologies")
    assert resp7.status_code == 200


def test_single_transaction_no_fabricated_zero_delta_t():
    """Verify that a single transaction never produces a fabricated 0.0s delta_t."""
    now = datetime.now(timezone.utc)
    t1 = now.isoformat()

    single_hop = TraceHopItem(
        hop_number=1,
        from_address="TSingleSourceWallet11111111111111",
        to_address="TSingleDestWallet2222222222222222",
        tx_hash="0xsinglehash11111111111111111111111111111111111111111111111111111111",
        asset="USDT",
        amount=100.0,
        timestamp=t1,
        delta_t_seconds=None,
        explorer_url="https://tronscan.org/#/transaction/0xsinglehash",
    )

    single_path = TracePathDetail(
        path_id="path-single-001",
        wallet_sequence=["TSingleSourceWallet11111111111111", "TSingleDestWallet2222222222222222"],
        hop_count=1,
        initial_amount=100.0,
        final_amount=100.0,
        value_retention_percent=100.0,
        elapsed_time_seconds=0.0,
        relevance_score=80.0,
        relevance_explanation=["Direct single-hop transfer"],
        hops=[single_hop],
    )

    trace_resp = TraceResultResponse(
        trace_id="tr-single-tx-001",
        starting_wallet="TSingleSourceWallet11111111111111",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=2,
        total_transactions_analyzed=1,
        total_edges_discovered=1,
        total_paths_found=1,
        started_at=now,
        completed_at=now,
        paths=[single_path],
    )

    detector = VelocityDetector()
    metrics = detector.analyze_trace_velocity(trace_resp)

    # 1. Delta_t metrics must be None, NOT 0.0s
    assert metrics.transfer_count == 1
    assert metrics.minimum_delta_t is None
    assert metrics.average_delta_t is None
    assert metrics.maximum_delta_t is None
    assert metrics.duration_seconds == 0.0

    # 2. Scorer must return 0.0 and LOW
    scorer = VelocityScorer()
    score, severity, reasons, components = scorer.score_velocity(metrics)
    assert score == 0.0
    assert severity == "LOW"
    assert components["minimum_delta_t"] == 0.0
    assert components["average_delta_t"] == 0.0

    # 3. EvidenceBuilder explanation must not claim fabricated 0.0s
    from app.velocity.evidence import VelocityEvidenceBuilder
    builder = VelocityEvidenceBuilder()
    explanation = builder.generate_explanation(score, severity, metrics, reasons)
    assert "0.0s" not in explanation
    assert "insufficient sequential transfers" in explanation or "N/A" in explanation


def test_distinct_transactions_same_block_zero_delta_t():
    """Verify that two distinct transactions sharing the same timestamp report a measured 0.0s delta_t."""
    now = datetime.now(timezone.utc)
    t_shared = now.isoformat()

    hop1 = TraceHopItem(
        hop_number=1,
        from_address="TWalletA111111111111111111111111",
        to_address="TWalletB222222222222222222222222",
        tx_hash="0xtx111111111111111111111111111111111111111111111111111111111111",
        asset="USDT",
        amount=500.0,
        timestamp=t_shared,
        delta_t_seconds=None,
        explorer_url="https://tronscan.org/#/transaction/0xtx1",
    )
    hop2 = TraceHopItem(
        hop_number=2,
        from_address="TWalletB222222222222222222222222",
        to_address="TWalletC333333333333333333333333",
        tx_hash="0xtx222222222222222222222222222222222222222222222222222222222222",
        asset="USDT",
        amount=500.0,
        timestamp=t_shared,
        delta_t_seconds=0.0,
        explorer_url="https://tronscan.org/#/transaction/0xtx2",
    )

    path = TracePathDetail(
        path_id="path-shared-block-001",
        wallet_sequence=["TWalletA111111111111111111111111", "TWalletB222222222222222222222222", "TWalletC333333333333333333333333"],
        hop_count=2,
        initial_amount=500.0,
        final_amount=500.0,
        value_retention_percent=100.0,
        elapsed_time_seconds=0.0,
        relevance_score=90.0,
        relevance_explanation=["Same-block sequential transfer"],
        hops=[hop1, hop2],
    )

    trace_resp = TraceResultResponse(
        trace_id="tr-same-block-001",
        starting_wallet="TWalletA111111111111111111111111",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
        started_at=now,
        completed_at=now,
        paths=[path],
    )

    detector = VelocityDetector()
    metrics = detector.analyze_trace_velocity(trace_resp)

    # 2 distinct transactions in same block: 0.0s is genuinely measured
    assert metrics.transfer_count == 2
    assert metrics.minimum_delta_t == 0.0
    assert metrics.average_delta_t == 0.0
    assert metrics.duration_seconds == 0.0


def test_initial_transfer_vs_downstream_activity_separation():
    """Verify that $0.01 initial transfer is separated from $69.31M downstream VASP/hot wallet activity."""
    now = datetime.now(timezone.utc)
    t1 = now.isoformat()
    t2 = datetime.fromtimestamp(now.timestamp() + 10.0, timezone.utc).isoformat()

    # Initial micro-transfer ($0.01) from starting wallet to Bybit hot wallet
    hop1 = TraceHopItem(
        hop_number=1,
        from_address="TGCCfE3KJiXA2LNiKCmLZ6DT6NdL1zDWPY",
        to_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY",
        tx_hash="0xmicrotransfer000000000000000000000000000000000000000000000000001",
        asset="USDT",
        amount=0.01,
        timestamp=t1,
        delta_t_seconds=None,
        explorer_url="https://tronscan.org/#/transaction/0xmicro1",
    )

    # Massive downstream activity ($69.31M) moved by Bybit hot wallet
    hop2 = TraceHopItem(
        hop_number=2,
        from_address="TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY",
        to_address="TDownstreamExchangeVault11111111111",
        tx_hash="0xdownstreamsweep0000000000000000000000000000000000000000000000002",
        asset="USDT",
        amount=69310000.0,
        timestamp=t2,
        delta_t_seconds=10.0,
        explorer_url="https://tronscan.org/#/transaction/0xsweep2",
    )

    path = TracePathDetail(
        path_id="path-bybit-sweep-001",
        wallet_sequence=["TGCCfE3KJiXA2LNiKCmLZ6DT6NdL1zDWPY", "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", "TDownstreamExchangeVault11111111111"],
        hop_count=2,
        initial_amount=0.01,
        final_amount=69310000.0,
        value_retention_percent=100.0,
        elapsed_time_seconds=10.0,
        relevance_score=85.0,
        relevance_explanation=["Initial micro-transfer into exchange endpoint followed by sweep"],
        hops=[hop1, hop2],
    )

    trace_resp = TraceResultResponse(
        trace_id="tr-bybit-split-001",
        starting_wallet="TGCCfE3KJiXA2LNiKCmLZ6DT6NdL1zDWPY",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
        started_at=now,
        completed_at=now,
        paths=[path],
    )

    detector = VelocityDetector()
    metrics = detector.analyze_trace_velocity(trace_resp)

    # Verify separation
    assert metrics.initial_transfer_amount == 0.01
    assert metrics.downstream_activity_amount == 69310000.0
    assert metrics.total_amount == 69310000.01

    # Verify evidence builder description explicitly distinguishes both amounts
    from app.velocity.evidence import VelocityEvidenceBuilder
    builder = VelocityEvidenceBuilder()
    explanation = builder.generate_explanation(85.0, "HIGH", metrics, ["RAPID_TRANSFER_SEQUENCE"])

    assert "INITIAL OBSERVED TRANSFER: $0.01 USDT" in explanation
    assert "DOWNSTREAM OBSERVED ACTIVITY: $69,310,000.00 USDT" in explanation


def test_rapid_peel_movement_no_fabricated_zero_delta_t():
    """Verify rapid peel movement does not report fabricated 0s for single hops."""
    now = datetime.now(timezone.utc)
    t1 = now.isoformat()

    hop1 = TraceHopItem(
        hop_number=1,
        from_address="TSourceWallet11111111111111111111",
        to_address="TIntermediateWallet2222222222222",
        tx_hash="0xhash1111",
        asset="USDT",
        amount=1000.0,
        timestamp=t1,
        delta_t_seconds=None,
        explorer_url="https://tronscan.org/#/transaction/0xhash1111",
    )

    path_single = TracePathDetail(
        path_id="path-single-hop-001",
        wallet_sequence=["TSourceWallet11111111111111111111", "TIntermediateWallet2222222222222"],
        hop_count=1,
        initial_amount=1000.0,
        final_amount=1000.0,
        value_retention_percent=100.0,
        elapsed_time_seconds=0.0,
        relevance_score=80.0,
        relevance_explanation=["Single hop"],
        hops=[hop1],
    )

    detector = TypologyDetector()
    result = detector._detect_rapid_peel([path_single])
    # Single-hop path cannot qualify as rapid peel movement
    assert result is None


def test_risk_presentation_contextual_vs_flow_risk():
    """Verify that flow/structural risk is retained while contextual risk is adjusted based on VASP context."""
    from app.schemas.velocity import VelocityAnalysisResponse, VelocityAlert
    from app.schemas.typology import TypologyAnalysisResponse, TypologyResult

    # Mock high-velocity alert
    now = datetime.now(timezone.utc)
    v_alert = VelocityAlert(
        alert_id="val-test-001",
        trace_id="tr-test-risk-001",
        severity="HIGH",
        velocity_score=85.0,
        transfer_count=5,
        total_amount=50000.0,
        duration_seconds=120.0,
        minimum_delta_t=15.0,
        average_delta_t=30.0,
        maximum_delta_t=60.0,
        unique_recipients=4,
        downstream_hops=3,
        supporting_transactions=["0xtx1", "0xtx2"],
        supporting_wallets=["TWalletA", "TWalletB"],
        reason_codes=["RAPID_SUCCESSIVE_TRANSFERS"],
        explanation="High velocity movement detected",
        analyzed_at=now,
    )

    v_resp = VelocityAnalysisResponse(
        trace_id="tr-test-risk-001",
        starting_wallet="TStartingWallet",
        chain="TRON",
        asset="USDT",
        has_high_velocity_pattern=True,
        status="RESOLVED_ALERT",
        summary="High velocity movement detected",
        alerts=[v_alert],
        metrics={"downstream_hops": 3, "unique_recipients": 4},
    )

    # Typology with verified service entity context
    typ_service = TypologyResult(
        typology_id="typ-service-001",
        typology_name="KNOWN_SERVICE_ENTITY",
        severity="LOW",
        description="Endpoint identified as verified VASP service",
        trigger_conditions=["Known VASP endpoint"],
        metrics={},
        supporting_transactions=[],
        supporting_wallets=[],
        supporting_paths=[],
        confidence=1.0,
        is_known_service=True,
    )

    t_resp = TypologyAnalysisResponse(
        trace_id="tr-test-risk-001",
        starting_wallet="TStartingWallet",
        chain="TRON",
        asset="USDT",
        has_typologies=True,
        status="PATTERNS_IDENTIFIED",
        summary="Known service entity identified",
        typologies=[typ_service],
    )

    scorer = RiskScorer()
    (
        final_risk_score,
        raw_risk_score,
        contextual_risk_score,
        contextual_interpretation,
        risk_level,
        components,
        factors,
        is_known_service,
        service_entity_context,
        mitigations,
    ) = scorer.calculate_risk_score(v_resp, t_resp)

    # Raw structural risk is calculated and preserved
    assert raw_risk_score > 0.0
    # Service entity context is True
    assert is_known_service is True
    assert service_entity_context is True
    # Contextual risk score is adjusted
    assert contextual_risk_score < raw_risk_score
    assert final_risk_score == contextual_risk_score
    # Cautionary non-criminal service entity mitigation is documented without guaranteeing lawfulness
    assert any("KNOWN_SERVICE_ENTITY" in m for m in mitigations)
    assert any("structural evidence" in m for m in mitigations)
