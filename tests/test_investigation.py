import os
import pytest
import shutil
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.trace import TraceRun, TraceEdge, TracePath
from app.models.investigation import InvestigationJob, InvestigationSnapshot
from app.models.finding import Finding
from app.schemas.investigation import (
    InvestigationStartRequest,
    InvestigationState,
)
from app.investigation.orchestrator import InvestigationOrchestrator
from app.sahyog.adapter import SahyogAdapter
from app.reporting.pdf_generator import PDFReportGenerator
from app.export.exporters import DataExporter
from app.evaluation.framework import EvaluationFramework, GroundTruthTestCase


@pytest.fixture
def sample_investigation_setup(db: Session):
    """Seed test database with Case, TraceRun, TracePath, and TraceEdge records."""
    case_id = "case-test-inv-001"
    target_wallet = "TTestTargetWallet11111111111111111"

    c = Case(
        case_id=case_id,
        investigator_id="INV-TEST-001",
        reported_wallet=target_wallet,
        chain="TRON",
        asset="USDT",
        description="Phase 6 Unit Test Case",
    )
    db.add(c)

    tr = TraceRun(
        trace_id="tr-test-inv-001",
        case_id=case_id,
        starting_wallet=target_wallet,
        chain="TRON",
        asset="USDT",
        status="COMPLETED",
        total_wallets_discovered=3,
        total_transactions_analyzed=2,
        total_edges_discovered=2,
        total_paths_found=1,
    )
    db.add(tr)

    tp = TracePath(
        path_id="path-inv-001",
        trace_id="tr-test-inv-001",
        wallet_sequence=[target_wallet, "THopWallet11111111111111111", "THopWallet22222222222222222"],
        hop_count=2,
        initial_amount=10000.0,
        final_amount=9800.0,
        value_retention_percent=98.0,
        elapsed_time_seconds=45.0,
        relevance_score=95.0,
        relevance_explanation=["High value retention rapid multi-hop path"],
        edge_sequence=["tx-inv-001", "tx-inv-002"],
    )
    db.add(tp)

    e1 = TraceEdge(
        tx_hash="tx-inv-001",
        trace_id="tr-test-inv-001",
        from_wallet=target_wallet,
        to_wallet="THopWallet11111111111111111",
        amount=10000.0,
        asset="USDT",
        timestamp=datetime.now(timezone.utc),
        delta_t_seconds=0.0,
        hop=1,
        explorer_url="https://tronscan.org/#/transaction/tx-inv-001",
    )
    e2 = TraceEdge(
        tx_hash="tx-inv-002",
        trace_id="tr-test-inv-001",
        from_wallet="THopWallet11111111111111111",
        to_wallet="THopWallet22222222222222222",
        amount=9800.0,
        asset="USDT",
        timestamp=datetime.now(timezone.utc),
        delta_t_seconds=45.0,
        hop=2,
        explorer_url="https://tronscan.org/#/transaction/tx-inv-002",
    )
    db.add(e1)
    db.add(e2)
    db.commit()

    return case_id, target_wallet


@pytest.mark.anyio
async def test_investigation_orchestrator_end_to_end(db: Session, sample_investigation_setup):
    case_id, target_wallet = sample_investigation_setup
    export_dir = f"exports/test_{case_id}"

    try:
        orchestrator = InvestigationOrchestrator(db)
        request = InvestigationStartRequest(
            wallet=target_wallet,
            chain="TRON",
            asset="USDT",
            max_hops=2,
            min_transfer_amount=0.0,
        )

        job_resp, summary, sahyog_pkg = await orchestrator.execute_investigation(
            request=request,
            case_id=case_id,
            export_dir=export_dir,
        )

        assert job_resp.status == InvestigationState.COMPLETED
        assert job_resp.progress_percent == 100.0
        assert summary.target_wallet == target_wallet
        assert summary.case_id == case_id
        assert summary.evidence_count > 0
        assert summary.total_wallets_traced > 0

        # Check SAHYOG package headers
        assert sahyog_pkg["sahyog_metadata"]["integration_status"] == "READY FOR AUTHORISED API INTEGRATION"
        assert sahyog_pkg["case_details"]["case_id"] == case_id

        # Verify export files generated
        assert os.path.exists(os.path.join(export_dir, "investigation_report.pdf"))
        assert os.path.exists(os.path.join(export_dir, "investigation_result.json"))
        assert os.path.exists(os.path.join(export_dir, "sahyog_package.json"))
        assert os.path.exists(os.path.join(export_dir, "trace_edges.csv"))
        assert os.path.exists(os.path.join(export_dir, "transactions.csv"))
        assert os.path.exists(os.path.join(export_dir, "trace_paths.csv"))
        assert os.path.exists(os.path.join(export_dir, "evidence.csv"))
        assert os.path.exists(os.path.join(export_dir, "alerts.csv"))

    finally:
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir, ignore_errors=True)


def test_investigation_state_machine_and_snapshot(db: Session, sample_investigation_setup):
    case_id, target_wallet = sample_investigation_setup

    job = InvestigationJob(
        job_id="job-state-test-001",
        case_id=case_id,
        target_wallet=target_wallet,
        chain="TRON",
        asset="USDT",
        status=InvestigationState.QUEUED.value,
        progress_percent=0.0,
        current_stage="QUEUED",
        parameters_snapshot={"wallet": target_wallet, "max_hops": 3},
    )
    db.add(job)

    snapshot = InvestigationSnapshot(
        snapshot_id="snap-test-001",
        job_id="job-state-test-001",
        case_id=case_id,
        target_wallet=target_wallet,
        chain="TRON",
        asset="USDT",
        parameters={"max_hops": 3},
        trace_graph_snapshot={"nodes": [], "edges": []},
        engine_version="1.0.0",
    )
    db.add(snapshot)
    db.commit()

    db_job = db.query(InvestigationJob).filter(InvestigationJob.job_id == "job-state-test-001").first()
    assert db_job is not None
    assert db_job.status == "QUEUED"
    assert db_job.snapshot is not None
    assert db_job.snapshot[0].engine_version == "1.0.0"


def test_sahyog_adapter():
    adapter = SahyogAdapter()
    assert adapter.INTEGRATION_STATUS == "READY FOR AUTHORISED API INTEGRATION"


def test_evaluation_framework():
    eval_fw = EvaluationFramework()

    gt_case = GroundTruthTestCase(
        case_id="case-eval-001",
        target_wallet="TTestEvalWallet1111111111111111",
        true_vasp_name="Binance Hot Wallet",
        true_vasp_address="TTestEvalWallet1111111111111111",
        true_paths=[["TTestEvalWallet1111111111111111", "TBoutiqueWallet222"]],
        has_high_velocity=True,
    )

    pred = {
        "case_id": "case-eval-001",
        "candidate_vasps": [{"vasp_name": "Binance Hot Wallet"}],
        "discovered_paths": [["TTestEvalWallet1111111111111111", "TBoutiqueWallet222"]],
        "has_high_velocity": True,
    }

    report = eval_fw.run_evaluation(
        ground_truth_cases=[gt_case],
        predictions=[pred],
        total_pipeline_seconds=2.5,
    )

    assert report.overall_status == "PASS"
    assert report.vasp_metrics.top_1_accuracy == 1.0
    assert report.velocity_metrics.precision == 1.0
    assert report.baseline_comparison.efficiency_multiplier > 10.0


def test_investigation_api_endpoints(client: TestClient, db: Session, sample_investigation_setup):
    case_id, target_wallet = sample_investigation_setup
    export_dir = f"exports/{case_id}"

    try:
        # 1. POST /api/v1/cases/{case_id}/investigate
        req_data = {
            "wallet": target_wallet,
            "chain": "TRON",
            "asset": "USDT",
            "max_hops": 2,
            "min_transfer_amount": 0.0,
            "investigator_id": "INV-API-TEST",
        }
        resp1 = client.post(f"/api/v1/cases/{case_id}/investigate", json=req_data)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["status"] == "COMPLETED"
        assert data1["progress_percent"] == 100.0

        # 2. GET /api/v1/cases/{case_id}/investigation
        resp2 = client.get(f"/api/v1/cases/{case_id}/investigation")
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["case_id"] == case_id

        # 3. GET /api/v1/cases/{case_id}/findings
        resp3 = client.get(f"/api/v1/cases/{case_id}/findings")
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert isinstance(data3, list)

        # 4. GET /api/v1/cases/{case_id}/evidence
        resp4 = client.get(f"/api/v1/cases/{case_id}/evidence")
        assert resp4.status_code == 200
        data4 = resp4.json()
        assert isinstance(data4, list)

        # 5. GET /api/v1/cases/{case_id}/summary
        resp5 = client.get(f"/api/v1/cases/{case_id}/summary")
        assert resp5.status_code == 200
        data5 = resp5.json()
        assert "risk_score" in data5
        assert "contextual_risk_score" in data5

        # 6. GET /api/v1/cases/{case_id}/sahyog-package
        resp6 = client.get(f"/api/v1/cases/{case_id}/sahyog-package")
        assert resp6.status_code == 200
        data6 = resp6.json()
        assert data6["sahyog_metadata"]["integration_status"] == "READY FOR AUTHORISED API INTEGRATION"

        # 7. GET /api/v1/cases/{case_id}/export/json
        resp7 = client.get(f"/api/v1/cases/{case_id}/export/json")
        assert resp7.status_code == 200

        # 8. GET /api/v1/cases/{case_id}/export/csv
        resp8 = client.get(f"/api/v1/cases/{case_id}/export/csv")
        assert resp8.status_code == 200
        data8 = resp8.json()
        assert len(data8["csv_files"]) > 0

        # 9. GET /api/v1/cases/{case_id}/report
        resp9 = client.get(f"/api/v1/cases/{case_id}/report")
        assert resp9.status_code == 200
        assert resp9.headers["content-type"] == "application/pdf"

        # 10. GET /api/v1/cases/{case_id}/dataset (New Phase A endpoint)
        resp10 = client.get(f"/api/v1/cases/{case_id}/dataset")
        assert resp10.status_code == 200
        data10 = resp10.json()
        assert "summary" in data10
        assert "trace_result" in data10
        assert "vasp_attribution" in data10
        assert "evidence" in data10
        assert "findings" in data10

    finally:
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir, ignore_errors=True)


def test_investigation_wallet_validation(client: TestClient):
    """Test that invalid TRON target wallets are properly validated and rejected."""
    # 1. Address does not start with 'T'
    resp = client.post(
        "/api/v1/cases/case-val-001/investigate",
        json={
            "wallet": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            "chain": "TRON",
            "asset": "USDT",
        },
    )
    assert resp.status_code == 400
    assert "TRON" in resp.json()["detail"]

    # 2. Address too short
    resp2 = client.post(
        "/api/v1/cases/case-val-002/investigate",
        json={
            "wallet": "T123",
            "chain": "TRON",
            "asset": "USDT",
        },
    )
    assert resp2.status_code == 400
    assert "too short" in resp2.json()["detail"].lower()


def test_investigation_case_custom_parameters(client: TestClient, db: Session, sample_investigation_setup):
    """Test investigation execution with custom case ID and specific depth parameters."""
    case_id, target_wallet = sample_investigation_setup
    custom_case_id = f"{case_id}-custom-depth"
    export_dir = f"exports/{custom_case_id}"

    try:
        req_data = {
            "wallet": target_wallet,
            "chain": "TRON",
            "asset": "USDT",
            "max_hops": 3,
            "min_transfer_amount": 50.0,
            "investigator_id": "INV-LEAD-007",
            "description": "Targeted deep trace investigation",
        }
        resp = client.post(f"/api/v1/cases/{custom_case_id}/investigate", json=req_data)
        assert resp.status_code == 200
        job_data = resp.json()
        assert job_data["status"] == "COMPLETED"
        assert job_data["case_id"] == custom_case_id
        assert job_data["parameters_snapshot"]["max_hops"] == 3
        assert job_data["parameters_snapshot"]["min_transfer_amount"] == 50.0

        # Verify dataset retrieval
        resp_dataset = client.get(f"/api/v1/cases/{custom_case_id}/dataset")
        assert resp_dataset.status_code == 200
        dataset = resp_dataset.json()
        assert dataset["summary"]["case_id"] == custom_case_id
        assert dataset["summary"]["target_wallet"] == target_wallet

    finally:
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir, ignore_errors=True)
