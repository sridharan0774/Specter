import pytest
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any

from app.intelligence.risk_engine import ExplainableGraphRiskEngine
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.velocity import VelocityAnalysisResponse, VelocityAlert
from app.schemas.typology import TypologyAnalysisResponse, TypologyResult
from app.schemas.vasp import VASPAttributionResponse, VASPAttributionCandidate



def _create_mock_trace_result(
    trace_id: str = "tr-test-01",
    starting_wallet: str = "TTESTWALLET111111111111111111111",
    chain: str = "TRON",
    asset: str = "USDT",
    hop_count: int = 1,
    paths_count: int = 1,
    tx_count: int = 1,
    retention_pct: float = 50.0,
    wallets_count: int = 2,
    min_delta: float = 300.0,
    avg_delta: float = 600.0,
    recipients_count: int = 1,
    downstream_hops: int = 1,
    total_amount: float = 1000.0,
) -> Tuple:
    hops = []
    for h in range(1, hop_count + 1):
        hops.append(
            TraceHopItem(
                hop_number=h,
                from_address=f"TWALLET_{h}",
                to_address=f"TWALLET_{h+1}",
                amount=total_amount,
                asset=asset,
                tx_hash=f"txhash_{h}_abc123def4567890",
                timestamp=datetime.now(timezone.utc).isoformat(),
                delta_t_seconds=min_delta if h > 1 else 0.0,
                explorer_url=f"https://tronscan.org/#/transaction/txhash_{h}",
            )
        )

    paths = []
    for p_idx in range(paths_count):
        paths.append(
            TracePathDetail(
                path_id=f"p-{p_idx+1}",
                wallet_sequence=[f"TWALLET_{i}" for i in range(1, hop_count + 2)],
                hop_count=hop_count,
                initial_amount=total_amount,
                final_amount=total_amount * (retention_pct / 100.0),
                value_retention_percent=retention_pct,
                elapsed_time_seconds=min_delta * hop_count,
                relevance_score=80.0,
                relevance_explanation=["Valid path"],
                cycle_detected=False,
                metrics={},
                hops=hops,
            )
        )

    trace = TraceResultResponse(
        trace_id=trace_id,
        starting_wallet=starting_wallet,
        chain=chain,
        asset=asset,
        status="COMPLETED",
        truncated=False,
        total_wallets_discovered=wallets_count,
        total_transactions_analyzed=tx_count,
        total_edges_discovered=tx_count,
        total_paths_found=paths_count,
        processing_time_seconds=0.1,
        started_at=datetime.now(timezone.utc).isoformat(),
        paths=paths,
    )

    metrics_dict = {
        "transfer_count": tx_count,
        "total_amount": total_amount,
        "initial_transfer_amount": total_amount,
        "duration_seconds": min_delta * max(1, tx_count - 1),
        "minimum_delta_t": min_delta if tx_count > 1 else None,
        "average_delta_t": avg_delta if tx_count > 1 else None,
        "maximum_delta_t": avg_delta * 1.5 if tx_count > 1 else None,
        "unique_recipients": recipients_count,
        "downstream_hops": downstream_hops,
        "velocity_score": 50.0 if tx_count >= 4 else 10.0,
    }

    vel = VelocityAnalysisResponse(
        trace_id=trace_id,
        starting_wallet=starting_wallet,
        chain=chain,
        asset=asset,
        has_high_velocity_pattern=tx_count >= 4,
        status="COMPLETED",
        summary="Velocity test summary",
        alerts=[],
        metrics=metrics_dict,
    )


    typ = TypologyAnalysisResponse(
        trace_id=trace_id,
        starting_wallet=starting_wallet,
        chain=chain,
        asset=asset,
        status="COMPLETED",
        summary="Typology test summary",
        typologies=[],
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )

    return trace, vel, typ


from typing import Tuple


def test_egre_insufficient_evidence():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=1, paths_count=1, hop_count=1)
    res = engine.evaluate_risk(trace, vel, typ)
    assert res.assessment_status == "INSUFFICIENT_EVIDENCE"
    assert res.risk_score is None
    assert res.risk_level is None


def test_egre_low_risk_isolated_transfer():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=2, hop_count=1, total_amount=100.0, min_delta=600.0)
    res = engine.evaluate_risk(trace, vel, typ)
    assert res.assessment_status == "ASSESSED"
    assert res.risk_level in ["LOW", "MODERATE"]
    assert res.risk_score < 50.0


def test_egre_rapid_movement_indicator():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=3, hop_count=2, min_delta=25.0)
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "RAPID_MOVEMENT" in ind_ids
    rapid_ind = next(i for i in res.indicators if i.indicator_id == "RAPID_MOVEMENT")
    assert rapid_ind.classification == "OBSERVED"
    assert rapid_ind.dimension == "TEMPORAL"


def test_egre_high_velocity_indicator():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=5, hop_count=2, min_delta=40.0)
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "HIGH_TRANSACTION_VELOCITY" in ind_ids


def test_egre_multi_hop_flow_indicator():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=3, hop_count=4, min_delta=500.0)
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "MULTI_HOP_FLOW" in ind_ids


def test_egre_fan_out_indicator():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=4, hop_count=2, recipients_count=5)
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "FAN_OUT" in ind_ids


def test_egre_potential_mixer_pattern_heuristic():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=3, hop_count=2)
    typ.typologies.append(
        TypologyResult(
            typology_id="typ-mixer-1",
            typology_name="TYPOLOGY_MIXER_PEEL_CHAIN",
            severity="HIGH",
            description="Peeling chain pattern matching heuristic obfuscation",
            trigger_conditions=["PEELING"],
            metrics={},
            supporting_transactions=["txhash_1_abc123def4567890"],
            supporting_wallets=["TWALLET_1"],
            supporting_paths=["p-1"],
            confidence=0.85,
            is_known_service=False,
        )
    )
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "POTENTIAL_MIXER_PATTERN" in ind_ids
    mixer_ind = next(i for i in res.indicators if i.indicator_id == "POTENTIAL_MIXER_PATTERN")
    assert mixer_ind.classification == "HEURISTIC"
    assert "CONFIRMED_MIXER" not in ind_ids


def test_egre_cross_chain_movement_indicator():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=3, hop_count=2)
    typ.typologies.append(
        TypologyResult(
            typology_id="typ-bridge-1",
            typology_name="TYPOLOGY_CROSS_CHAIN_BRIDGE",
            severity="MODERATE",
            description="Cross chain asset bridge movement",
            trigger_conditions=["BRIDGE"],
            metrics={},
            supporting_transactions=["txhash_1_abc123def4567890"],
            supporting_wallets=["TWALLET_1"],
            supporting_paths=["p-1"],
            confidence=0.90,
            is_known_service=True,
        )
    )
    res = engine.evaluate_risk(trace, vel, typ)
    ind_ids = [i.indicator_id for i in res.indicators]
    assert "CROSS_CHAIN_MOVEMENT" in ind_ids
    from app.schemas.vasp import VASPAttributionResponse, VASPAttributionCandidate


def test_egre_verified_vasp_interaction_does_not_force_high_risk():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=2, hop_count=1, total_amount=1000.0, min_delta=800.0)
    vasp_resp = VASPAttributionResponse(
        attribution_id="attr-test-01",
        trace_id=trace.trace_id,
        starting_wallet=trace.starting_wallet,
        chain=trace.chain,
        asset=trace.asset,
        status="RESOLVED",
        explanation="High confidence VASP attribution candidate Binance resolved.",
        evaluated_at=datetime.now(timezone.utc),
        candidates=[
            VASPAttributionCandidate(
                rank=1,
                candidate_name="Binance",
                attribution_confidence=95.0,
                confidence_band="HIGH",
                endpoint_address="TWALLET_2",
                entity_role="EXCHANGE_HOT_WALLET",
                attribution_type="DEPOSIT_ADDRESS",
                endpoint_hop_distance=1,
                source_confidence=1.0,
            )
        ],
    )
    res = engine.evaluate_risk(trace, vel, typ, vasp_resp=vasp_resp)
    assert res.risk_level != "HIGH"
    assert res.risk_level != "VERY HIGH"
    assert res.is_known_service_entity is True


def test_egre_correlation_control_dimension_caps():
    engine = ExplainableGraphRiskEngine()
    # Trigger multiple temporal indicators (RAPID_MOVEMENT + HIGH_TRANSACTION_VELOCITY)
    trace, vel, typ = _create_mock_trace_result(tx_count=6, hop_count=3, min_delta=10.0, avg_delta=20.0)
    res = engine.evaluate_risk(trace, vel, typ)
    temporal_score = res.dimension_scores.get("temporal", 0.0)
    assert temporal_score <= 25.0


def test_egre_reproducibility():
    engine = ExplainableGraphRiskEngine()
    trace, vel, typ = _create_mock_trace_result(tx_count=4, hop_count=2, min_delta=45.0)
    res1 = engine.evaluate_risk(trace, vel, typ)
    res2 = engine.evaluate_risk(trace, vel, typ)
    assert res1.risk_score == res2.risk_score
    assert res1.risk_level == res2.risk_level
    assert [i.indicator_id for i in res1.indicators] == [i.indicator_id for i in res2.indicators]
