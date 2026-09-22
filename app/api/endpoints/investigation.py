import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.investigation import InvestigationJob
from app.schemas.investigation import (
    InvestigationStartRequest,
    InvestigationJobResponse,
    FindingSchema,
    EvidenceGraphItemSchema,
    InvestigationSummarySchema,
)
from app.investigation.orchestrator import InvestigationOrchestrator

router = APIRouter()


@router.post("/cases/{case_id}/investigate", response_model=InvestigationJobResponse, summary="Execute Full Specter Investigation Pipeline")
async def start_case_investigation(
    case_id: str,
    request: InvestigationStartRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers the complete 13-stage automated investigation pipeline for a target wallet under a case.
    Executes tracing, pattern analysis, VASP attribution, evidence building, report generation, and SAHYOG package creation.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        # Create case if not existing
        case = Case(
            case_id=case_id,
            investigator_id=request.investigator_id or "INV-AUTOMATED-001",
            reported_wallet=request.wallet,
            chain=request.chain,
            asset=request.asset,
            description=request.description,
        )
        db.add(case)
        db.commit()

    orchestrator = InvestigationOrchestrator(db)
    try:
        job_resp, summary, sahyog_pkg = await orchestrator.execute_investigation(
            request=request,
            case_id=case_id,
        )
        return job_resp
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation pipeline execution failed: {str(e)}",
        )


@router.get("/cases/{case_id}/investigation", response_model=InvestigationJobResponse, summary="Get Investigation Job Status")
def get_investigation_job_status(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve latest investigation job status and progress percentage (0-100%) for a case.
    """
    job = (
        db.query(InvestigationJob)
        .filter(InvestigationJob.case_id == case_id)
        .order_by(InvestigationJob.started_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No investigation jobs found for case '{case_id}'.",
        )
    return InvestigationJobResponse.model_validate(job)


@router.get("/cases/{case_id}/findings", response_model=List[FindingSchema], summary="Get Case Findings")
def get_case_findings(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve all analytical findings generated for a case.
    """
    orchestrator = InvestigationOrchestrator(db)
    return orchestrator.get_findings(case_id)


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceGraphItemSchema], summary="Get Case Evidence Ledger")
def get_case_evidence(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve traceable evidence graph items for a case.
    """
    orchestrator = InvestigationOrchestrator(db)
    return orchestrator.get_evidence(case_id)


@router.get("/cases/{case_id}/summary", summary="Get Structured Investigation Summary")
def get_investigation_summary(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve structured investigation summary containing risk indicators, VASP resolution, alerts, and execution metrics.
    """
    export_dir = os.path.join("exports", case_id)
    json_path = os.path.join(export_dir, "investigation_result.json")
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed investigation result found for case '{case_id}'. Execute investigation first.",
        )
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", data)


@router.get("/cases/{case_id}/dataset", summary="Get Full Consolidated Investigation Dataset")
def get_investigation_dataset(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve full consolidated investigation dataset containing summary, risk indicators,
    VASP attribution, findings, evidence ledger, velocity, typologies, and fund-tracing graph.
    """
    export_dir = os.path.join("exports", case_id)
    json_path = os.path.join(export_dir, "investigation_result.json")
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completed investigation dataset found for case '{case_id}'. Execute investigation first.",
        )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/cases/{case_id}/report", summary="Generate Investigation PDF Report")
async def generate_case_pdf_report(
    case_id: str,
    request: InvestigationStartRequest,
    db: Session = Depends(get_db),
):
    """
    Executes pipeline and generates PDF report 'INVESTIGATION-READY BLOCKCHAIN INTELLIGENCE REPORT'.
    """
    orchestrator = InvestigationOrchestrator(db)
    job_resp, summary, sahyog_pkg = await orchestrator.execute_investigation(
        request=request,
        case_id=case_id,
    )
    pdf_path = os.path.join("exports", case_id, "investigation_report.pdf")
    return {
        "case_id": case_id,
        "pdf_report_path": pdf_path,
        "status": "GENERATED",
        "job_id": job_resp.job_id,
    }


@router.get("/cases/{case_id}/report", summary="Download Investigation PDF Report")
def download_case_pdf_report(
    case_id: str,
):
    """
    Download generated PDF report file for a case.
    """
    pdf_path = os.path.join("exports", case_id, "investigation_report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF report for case '{case_id}' not found. Generate report first.",
        )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"SPECTER_INTELLIGENCE_REPORT_{case_id}.pdf",
    )


@router.get("/cases/{case_id}/export/json", summary="Download Investigation JSON Result")
def export_case_json(
    case_id: str,
):
    """
    Download complete investigation JSON dataset.
    """
    json_path = os.path.join("exports", case_id, "investigation_result.json")
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export JSON for case '{case_id}' not found.",
        )
    return FileResponse(
        path=json_path,
        media_type="application/json",
        filename=f"investigation_result_{case_id}.json",
    )


@router.get("/cases/{case_id}/export/csv", summary="List / Export Case CSV Datasets")
def export_case_csvs(
    case_id: str,
):
    """
    Retrieve paths to exported CSV datasets (transactions.csv, trace_edges.csv, trace_paths.csv, vasp_candidates.csv, evidence.csv, alerts.csv).
    """
    export_dir = os.path.join("exports", case_id)
    if not os.path.exists(export_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export directory for case '{case_id}' not found.",
        )
    csv_files = [f for f in os.listdir(export_dir) if f.endswith(".csv")]
    return {
        "case_id": case_id,
        "csv_files": csv_files,
        "export_dir": os.path.abspath(export_dir),
    }


@router.get("/cases/{case_id}/sahyog-package", summary="Get SAHYOG-Ready Intelligence Export Package")
def get_sahyog_package(
    case_id: str,
):
    """
    Retrieve SAHYOG-ready structured export package.
    Marked with: SAHYOG INTEGRATION STATUS: READY FOR AUTHORISED API INTEGRATION.
    """
    sahyog_path = os.path.join("exports", case_id, "sahyog_package.json")
    if not os.path.exists(sahyog_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SAHYOG package for case '{case_id}' not found.",
        )
    with open(sahyog_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
    return pkg
