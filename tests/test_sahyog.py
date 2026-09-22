import pytest
import os
import json
from fastapi.testclient import TestClient
from app.main import app
from app.sahyog.adapter import SahyogAdapter, LocalPackageTransport
from app.schemas.investigation import InvestigationSummarySchema
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.vasp import VASPAttributionResponse, VASPAttributionCandidate
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.sahyog import SahyogRequestResponse, SahyogValidationResult
from app.models.sahyog import SahyogRequest


@pytest.fixture
def mock_investigation_components():
    summary = InvestigationSummarySchema(
        case_id="case-sahyog-test-01",
        job_id="job-sahyog-test-01",
        target_wallet="TBpr1tQ5kvo79GmMDTbQL",
        chain="TRON",
        asset="USDT",
        investigation_status="COMPLETED",
        execution_duration_seconds=1.2,
        total_wallets_traced=5,
        total_transactions_analyzed=12,
        total_paths_found=3,
        risk_score=88.5,
        raw_risk_score=85.0,
        contextual_risk_score=88.5,
        risk_level="HIGH",
        is_known_service_entity=True,
        service_entity_context=True,
        contextual_interpretation="High Risk Flow",
        evidence_count=4,
    )


    vasp_candidate = VASPAttributionCandidate(
        rank=1,
        candidate_name="Bybit Exchange",
        entity_role="VASP",
        endpoint_address="TBpr1tQ5kvo79GmMDTbQL",
        chain="TRON",
        attribution_type="EXCHANGE_DEPOSIT_ENDPOINT",
        attribution_confidence=100.0,
        source_confidence=0.98,
        confidence_band="HIGH",
        endpoint_hop_distance=1,
        matched_relevance_reasons=["Direct 1-hop deposit endpoint match to verified Bybit wallet"],
        supporting_transactions=["3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227"],
        supporting_wallets=["TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL", "TBpr1tQ5kvo79GmMDTbQL"],
    )

    vasp_resp = VASPAttributionResponse(
        attribution_id="attr-001",
        trace_id="trace-001",
        case_id="case-sahyog-test-01",
        starting_wallet="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        chain="TRON",
        resolution_status="RESOLVED",
        status="RESOLVED",
        explanation="Verified Bybit Deposit Endpoint",
        evaluated_at="2026-09-22T08:00:00Z",
        has_high_confidence_match=True,
        candidates=[vasp_candidate],
    )


    trace_result = TraceResultResponse(
        trace_id="trace-001",
        case_id="case-sahyog-test-01",
        starting_wallet="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        truncated=False,
        total_wallets_discovered=5,
        total_transactions_analyzed=12,
        total_edges_discovered=8,
        total_paths_found=1,
        processing_time_seconds=0.45,
        started_at="2026-09-22T08:00:00Z",
        paths=[

            TracePathDetail(
                path_id="path-1",
                wallet_sequence=["TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL", "TBpr1tQ5kvo79GmMDTbQL"],
                hop_count=1,
                initial_amount=1000.0,
                final_amount=1000.0,
                value_retention_percent=100.0,
                elapsed_time_seconds=120.0,
                relevance_score=0.95,
                relevance_explanation=["Direct hop to exchange deposit endpoint"],
                cycle_detected=False,
                metrics={},
                hops=[
                    TraceHopItem(
                        hop_number=1,
                        from_address="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
                        to_address="TBpr1tQ5kvo79GmMDTbQL",
                        tx_hash="3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227",
                        asset="USDT",
                        amount=1000.0,
                        timestamp="2026-09-22T08:00:00Z",
                        delta_t_seconds=120.0,
                        explorer_url="https://tronscan.org/#/transaction/3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227",
                    )
                ],
            )
        ],
    )

    velocity_resp = VelocityAnalysisResponse(
        trace_id="trace-001",
        starting_wallet="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        chain="TRON",
        asset="USDT",
        has_high_velocity_pattern=False,
        status="COMPLETED",
        summary="Standard velocity",
        alerts=[],
        metrics={},
    )

    typology_resp = TypologyAnalysisResponse(
        trace_id="trace-001",
        starting_wallet="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        summary="No laundering typologies",
        typologies=[],
        analyzed_at="2026-09-22T08:00:00Z",
    )

    risk_resp = RiskIndicatorResponse(
        trace_id="trace-001",
        starting_wallet="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        chain="TRON",
        asset="USDT",
        risk_score=88.5,
        raw_risk_score=85.0,
        contextual_risk_score=88.5,
        contextual_interpretation="High Risk Flow",
        risk_level="HIGH",
        component_contributions={},
        contributing_factors=["Exchange deposit hop"],
        is_known_service_entity=True,
        service_entity_context=True,
        false_positive_mitigations=[],
        analyzed_at="2026-09-22T08:00:00Z",
    )

    return summary, vasp_resp, trace_result, velocity_resp, typology_resp, risk_resp


def test_build_disclosure_request(mock_investigation_components):
    summary, vasp_resp, trace_result, velocity_resp, typology_resp, risk_resp = mock_investigation_components
    adapter = SahyogAdapter()

    req = adapter.build_disclosure_request(
        summary=summary,
        vasp_resp=vasp_resp,
        evidence_items=[],
        trace_result=trace_result,
        investigator_id="INV-TEST-007",
    )

    assert req["request_type"] == "DISCLOSURE_REQUEST"
    assert req["status"] == "DRAFT_REQUIRES_AUTHORISED_REVIEW"
    assert req["integration_status"] == "READY FOR AUTHORISED API INTEGRATION"

    assert req["case"]["case_id"] == summary.case_id
    assert req["case"]["investigation_id"] == summary.job_id
    assert req["case"]["investigator_reference"] == "INV-TEST-007"
    assert req["attribution"]["vasp"] == "Bybit Exchange"
    assert req["attribution"]["attribution_score"] == 100.0
    assert req["attribution"]["confidence"] == "HIGH"
    assert len(req["evidence_chain"]) == 7
    assert req["requested_action"]["type"] == "DISCLOSURE_REQUEST"


def test_build_freeze_request(mock_investigation_components):
    summary, vasp_resp, trace_result, velocity_resp, typology_resp, risk_resp = mock_investigation_components
    adapter = SahyogAdapter()

    req = adapter.build_freeze_request(
        summary=summary,
        vasp_resp=vasp_resp,
        evidence_items=[],
        trace_result=trace_result,
        investigator_id="INV-TEST-007",
        urgency_level="CRITICAL",
    )

    assert req["request_type"] == "ASSET_PRESERVATION_OR_FREEZE_REQUEST"
    assert req["status"] == "DRAFT_REQUIRES_AUTHORISED_REVIEW"
    assert req["urgency_level"] == "CRITICAL"
    assert req["attribution"]["vasp"] == "Bybit Exchange"
    assert req["attribution"]["wallet_address"] == "TBpr1tQ5kvo79GmMDTbQL"
    assert len(req["evidence_chain"]) == 7
    assert req["requested_action"]["type"] == "ASSET_PRESERVATION_OR_FREEZE_REQUEST"


def test_sahyog_package_validation(mock_investigation_components):
    summary, vasp_resp, trace_result, velocity_resp, typology_resp, risk_resp = mock_investigation_components
    adapter = SahyogAdapter()

    pkg = adapter.build_sahyog_package(
        summary=summary,
        findings=[],
        evidence_items=[],
        trace_result=trace_result,
        velocity_resp=velocity_resp,
        typology_resp=typology_resp,
        risk_resp=risk_resp,
        vasp_resp=vasp_resp,
    )

    val_res = adapter.validate_sahyog_package(pkg)
    assert val_res["valid"] is True
    assert val_res["status"] == "PACKAGE VALID"
    assert len(val_res["errors"]) == 0


def test_sahyog_package_validation_invalid():
    adapter = SahyogAdapter()
    invalid_pkg = {
        "sahyog_metadata": {"integration_status": "READY_FOR_AUTHORISED_API_INTEGRATION"},
        "case_details": {},  # missing case_id, job_id, target_wallet
    }

    val_res = adapter.validate_sahyog_package(invalid_pkg)
    assert val_res["valid"] is False
    assert val_res["status"] == "PACKAGE INVALID"
    assert len(val_res["errors"]) > 0


def test_sahyog_transport_submit_contract():
    adapter = SahyogAdapter()
    res = adapter.submit({"test": "payload"})

    assert res["status"] == "DRAFT_REQUIRES_AUTHORISED_REVIEW"
    assert res["integration_status"] == "READY FOR AUTHORISED API INTEGRATION"

    assert "NO AUTOMATED EXTERNAL SUBMISSION EXECUTED" in res["notice"]
    assert res["external_receipt_id"] is None


def test_sahyog_api_endpoints():
    client = TestClient(app)

    # 1. Create a case
    c_res = client.post("/api/v1/cases", json={
        "reported_wallet": "TBpr1tQ5kvo79GmMDTbQL",
        "chain": "TRON",
        "asset": "USDT",
        "investigator_id": "INV-TEST-API",
        "description": "API Test Case"
    })
    assert c_res.status_code == 201
    cid = c_res.json()["case_id"]

    # 2. Run investigation
    inv_res = client.post(f"/api/v1/cases/{cid}/investigate", json={
        "wallet": "TBpr1tQ5kvo79GmMDTbQL",
        "chain": "TRON",
        "asset": "USDT",
        "max_hops": 1,
        "investigator_id": "INV-TEST-API"
    })
    assert inv_res.status_code == 200

    # 3. Test disclosure request endpoint
    disc_res = client.post(f"/api/v1/cases/{cid}/sahyog/disclosure-request")
    assert disc_res.status_code == 200
    d_json = disc_res.json()
    assert d_json["request_type"] == "DISCLOSURE_REQUEST"
    assert d_json["status"] == "DRAFT_REQUIRES_AUTHORISED_REVIEW"
    assert d_json["attribution_score"] >= 0.0

    # 4. Test freeze request endpoint
    freeze_res = client.post(f"/api/v1/cases/{cid}/sahyog/freeze-request")
    assert freeze_res.status_code == 200
    f_json = freeze_res.json()
    assert f_json["request_type"] == "ASSET_PRESERVATION_OR_FREEZE_REQUEST"

    # 5. Test validation endpoint
    val_res = client.post(f"/api/v1/cases/{cid}/sahyog/validate")
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # 6. Test contract status endpoint
    st_res = client.get(f"/api/v1/cases/{cid}/sahyog/status")
    assert st_res.status_code == 200
    assert st_res.json()["integration_status"] == "READY_FOR_AUTHORISED_API_INTEGRATION"

    # 7. Test list requests endpoint
    reqs_res = client.get(f"/api/v1/cases/{cid}/sahyog/requests")
    assert reqs_res.status_code == 200
    assert len(reqs_res.json()) >= 2
