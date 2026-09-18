from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.trace import TraceRun
from app.models.vasp import VASPAttribution
from app.schemas.vasp import VASPAttributionResponse, VASPAttributionCandidate
from app.vasp.service import VASPService

router = APIRouter()


@router.post("/cases/{case_id}/vasp-resolve", response_model=VASPAttributionResponse, summary="Resolve VASP Attribution for Case")
def resolve_case_vasp_attribution(
    case_id: str,
    trace_id: Optional[str] = Query(None, description="Optional specific trace_id to evaluate for this case"),
    db: Session = Depends(get_db),
):
    """
    Perform analytical, source-backed VASP attribution on a multi-hop trace fund flow graph for a case.
    Identifies candidate VASPs, calculates source and attribution confidence scores, and constructs an evidence ledger.
    If evidence is insufficient (<40 confidence), returns 'NO HIGH-CONFIDENCE VASP IDENTIFIED'.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    service = VASPService(db)

    # Find trace run to use
    if trace_id:
        trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id, TraceRun.case_id == case_id).first()
        if not trace_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace run '{trace_id}' for case '{case_id}' not found.",
            )
    else:
        # Use latest trace run for case
        trace_run = (
            db.query(TraceRun)
            .filter(TraceRun.case_id == case_id)
            .order_by(TraceRun.started_at.desc())
            .first()
        )
        if not trace_run:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No trace runs exist for case '{case_id}'. Execute a trace first via POST /api/v1/cases/{case_id}/trace.",
            )

    return service.resolve_from_trace_id(trace_id=trace_run.trace_id, case_id=case_id)


@router.get("/cases/{case_id}/vasp-candidates", response_model=VASPAttributionResponse, summary="Get VASP Candidates for Case")
def get_case_vasp_candidates(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve current VASP candidates and attribution resolution for a specific case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    service = VASPService(db)
    trace_run = (
        db.query(TraceRun)
        .filter(TraceRun.case_id == case_id)
        .order_by(TraceRun.started_at.desc())
        .first()
    )
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace evaluations found for case '{case_id}'.",
        )

    return service.resolve_from_trace_id(trace_id=trace_run.trace_id, case_id=case_id)


@router.post("/trace/{trace_id}/vasp-resolve", response_model=VASPAttributionResponse, summary="Resolve VASP Attribution for Trace ID")
def resolve_trace_vasp_attribution(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Perform analytical VASP attribution evaluation directly on a specific multi-hop trace run.
    """
    trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace run '{trace_id}' not found.",
        )

    service = VASPService(db)
    return service.resolve_from_trace_id(trace_id=trace_id)


@router.get("/trace/{trace_id}/vasp-candidates", response_model=VASPAttributionResponse, summary="Get VASP Candidates for Trace ID")
def get_trace_vasp_candidates(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve VASP attribution candidates for a specific trace ID.
    """
    trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace run '{trace_id}' not found.",
        )

    service = VASPService(db)
    return service.resolve_from_trace_id(trace_id=trace_id)
