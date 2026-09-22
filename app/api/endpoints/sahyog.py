import os
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.investigation import InvestigationJob, InvestigationSnapshot
from app.models.sahyog import SahyogRequest
from app.schemas.sahyog import (
    SahyogDisclosureRequestCreate,
    SahyogFreezeRequestCreate,
    SahyogRequestResponse,
    SahyogValidationResult,
    SahyogStatusContractResponse,
)
from app.sahyog.adapter import SahyogAdapter
from app.investigation.orchestrator import InvestigationOrchestrator

logger = logging.getLogger("specter.api.sahyog")

router = APIRouter()


def _get_case_and_investigation_data(case_id: str, db: Session):
    """Helper to reconstruct investigation objects for request generation."""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    orchestrator = InvestigationOrchestrator(db)
    
    # Check export directory for existing result
    export_dir = os.path.join("exports", case_id)
    json_path = os.path.join(export_dir, "investigation_result.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No completed investigation execution found for case '{case_id}'. Run investigation first via POST /api/v1/cases/{case_id}/investigate.",
        )

    with open(json_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    findings = orchestrator.get_findings(case_id)
    evidence_items = orchestrator.get_evidence(case_id)

    # Reconstruct responses from stored json
    from app.schemas.investigation import InvestigationSummarySchema
    from app.schemas.trace import TraceResultResponse
    from app.schemas.vasp import VASPAttributionResponse

    summary_raw = full_data.get("summary", full_data)
    summary = InvestigationSummarySchema.model_validate(summary_raw)
    
    trace_raw = full_data.get("trace_result", {})
    trace_result = TraceResultResponse.model_validate(trace_raw) if trace_raw else None
    
    vasp_raw = full_data.get("vasp_attribution", {})
    vasp_resp = VASPAttributionResponse.model_validate(vasp_raw) if (vasp_raw and "candidates" in vasp_raw) else None

    if not trace_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trace result dataset unavailable for case '{case_id}'.",
        )

    return case, summary, vasp_resp, evidence_items, trace_result


@router.post("/cases/{case_id}/sahyog/disclosure-request", response_model=SahyogRequestResponse, summary="Prepare VASP Disclosure Request")
def prepare_disclosure_request(
    case_id: str,
    body: Optional[SahyogDisclosureRequestCreate] = None,
    db: Session = Depends(get_db),
):
    """
    Builds, validates, and persists an evidence-linked VASP Information Disclosure Request draft.
    Explicit status: DRAFT_REQUIRES_AUTHORISED_REVIEW.
    """
    req_body = body or SahyogDisclosureRequestCreate()
    case, summary, vasp_resp, evidence_items, trace_result = _get_case_and_investigation_data(case_id, db)

    adapter = SahyogAdapter()
    req_dict = adapter.build_disclosure_request(
        summary=summary,
        vasp_resp=vasp_resp,
        evidence_items=evidence_items,
        trace_result=trace_result,
        investigator_id=req_body.investigator_id or case.investigator_id,
        reason=req_body.reason_for_request,
    )

    # Validate generated request
    val_res = adapter.validate_sahyog_package(req_dict)
    req_dict["validation_result"] = val_res

    # Export to disk
    export_dir = os.path.join("exports", case_id)
    filepath = adapter.export_sahyog_package(req_dict, output_dir=export_dir, filename="sahyog_disclosure_request.json")

    # Extract fields for DB record
    attr = req_dict.get("attribution", {})
    
    db_req = SahyogRequest(
        request_id=req_dict["request_id"],
        case_id=case_id,
        job_id=summary.job_id,
        request_type="DISCLOSURE_REQUEST",
        status="DRAFT_REQUIRES_AUTHORISED_REVIEW",
        package_version="1.0",
        integration_status=adapter.INTEGRATION_STATUS,
        target_wallet=summary.target_wallet,
        chain=summary.chain,
        asset=summary.asset,
        attributed_vasp=attr.get("vasp"),
        endpoint_address=attr.get("wallet_address"),
        attribution_score=float(attr.get("attribution_score", 0.0)),
        confidence_level=str(attr.get("confidence", "HIGH")),
        hop_distance=int(attr.get("hop_distance", 0)),
        endpoint_status=str(attr.get("endpoint_status", "TERMINAL ENDPOINT")),
        validation_result=val_res,
        request_data=req_dict,
        evidence_chain=req_dict.get("evidence_chain"),
        evidence_snapshot_reference=req_dict.get("evidence_snapshot_reference"),
        exported_path=filepath,
        investigator_id=req_body.investigator_id or case.investigator_id,
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)

    return db_req


@router.post("/cases/{case_id}/sahyog/freeze-request", response_model=SahyogRequestResponse, summary="Prepare Asset Preservation / Freeze Request")
def prepare_freeze_request(
    case_id: str,
    body: Optional[SahyogFreezeRequestCreate] = None,
    db: Session = Depends(get_db),
):
    """
    Builds, validates, and persists an evidence-linked Asset Preservation / Freeze Request draft.
    Explicit status: DRAFT_REQUIRES_AUTHORISED_REVIEW.
    """
    req_body = body or SahyogFreezeRequestCreate()
    case, summary, vasp_resp, evidence_items, trace_result = _get_case_and_investigation_data(case_id, db)

    adapter = SahyogAdapter()
    req_dict = adapter.build_freeze_request(
        summary=summary,
        vasp_resp=vasp_resp,
        evidence_items=evidence_items,
        trace_result=trace_result,
        investigator_id=req_body.investigator_id or case.investigator_id,
        reason=req_body.reason_for_request,
        urgency_level=req_body.urgency_level,
    )

    val_res = adapter.validate_sahyog_package(req_dict)
    req_dict["validation_result"] = val_res

    export_dir = os.path.join("exports", case_id)
    filepath = adapter.export_sahyog_package(req_dict, output_dir=export_dir, filename="sahyog_freeze_request.json")

    attr = req_dict.get("attribution", {})

    db_req = SahyogRequest(
        request_id=req_dict["request_id"],
        case_id=case_id,
        job_id=summary.job_id,
        request_type="ASSET_PRESERVATION_OR_FREEZE_REQUEST",
        status="DRAFT_REQUIRES_AUTHORISED_REVIEW",
        package_version="1.0",
        integration_status=adapter.INTEGRATION_STATUS,
        target_wallet=summary.target_wallet,
        chain=summary.chain,
        asset=summary.asset,
        attributed_vasp=attr.get("vasp"),
        endpoint_address=attr.get("wallet_address"),
        attribution_score=float(attr.get("attribution_score", 0.0)),
        confidence_level=str(attr.get("confidence", "HIGH")),
        hop_distance=int(attr.get("hop_distance", 0)),
        endpoint_status=str(attr.get("endpoint_status", "TERMINAL ENDPOINT")),
        validation_result=val_res,
        request_data=req_dict,
        evidence_chain=req_dict.get("evidence_chain"),
        evidence_snapshot_reference=req_dict.get("evidence_snapshot_reference"),
        exported_path=filepath,
        investigator_id=req_body.investigator_id or case.investigator_id,
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)

    return db_req


@router.post("/cases/{case_id}/sahyog/validate", response_model=SahyogValidationResult, summary="Validate SAHYOG Package Completeness")
def validate_sahyog_package_endpoint(
    case_id: str,
    package_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
):
    """
    Validates package or request fields against mandatory field completeness rules.
    Returns PACKAGE VALID or PACKAGE INVALID with error details.
    """
    adapter = SahyogAdapter()
    if package_data:
        return adapter.validate_sahyog_package(package_data)

    # Check latest sahyog package on disk
    pkg_path = os.path.join("exports", case_id, "sahyog_package.json")
    if not os.path.exists(pkg_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SAHYOG package for case '{case_id}' not found.",
        )
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    return adapter.validate_sahyog_package(pkg)


@router.get("/cases/{case_id}/sahyog/status", response_model=SahyogStatusContractResponse, summary="Get SAHYOG Integration Contract Status")
def get_sahyog_contract_status(case_id: str):
    """
    Returns current integration contract status explicitly distinguishing
    IMPLEMENTED vs READY FOR AUTHORISED API INTEGRATION vs FUTURE SCOPE.
    """
    return SahyogStatusContractResponse(
        integration_status="READY_FOR_AUTHORISED_API_INTEGRATION",
        generator_engine="Specter High-Velocity Blockchain Intelligence Platform v1.0",
        contract_notice="READY FOR AUTHORISED API INTEGRATION — NO LIVE UNLESS AUTHORISED",
        implemented_features=[
            "TRON/TRC20 live blockchain tracing",
            "Multi-hop fund flow graph analysis",
            "VASP entity intelligence matching",
            "Evidence-backed dual confidence scoring",
            "Velocity & transaction typology detection",
            "Investigation report generation (PDF & JSON)",
            "SAHYOG Disclosure Request builder",
            "SAHYOG Asset Preservation / Freeze Request builder",
            "Evidence chain traceability linking",
            "SAHYOG package validation engine",
            "Local SAHYOG JSON export transport",
        ],
        ready_for_integration_features=[
            "Official SAHYOG API submission transport",
            "External portal request acknowledgement",
            "Automated request status synchronization",
            "Authorised agency key management",
        ],
        future_scope_features=[
            "Additional blockchain adapters (EVM, BTC, Solana)",
            "Cross-chain bridge fund tracking",
            "Advanced mixer attribution logic",
        ],
    )


@router.get("/cases/{case_id}/sahyog/requests", response_model=List[SahyogRequestResponse], summary="List Prepared SAHYOG Requests for Case")
def list_case_sahyog_requests(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns list of all prepared SAHYOG requests (disclosure and freeze drafts) for a case.
    """
    reqs = (
        db.query(SahyogRequest)
        .filter(SahyogRequest.case_id == case_id)
        .order_by(SahyogRequest.created_at.desc())
        .all()
    )
    return reqs
