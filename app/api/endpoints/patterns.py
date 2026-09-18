from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.trace import TraceRun
from app.models.alert import Alert
from app.schemas.velocity import VelocityAnalysisResponse, VelocityAlert
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.velocity.service import VelocityService
from app.typologies.service import TypologyService
from app.risk.service import RiskService

router = APIRouter()


@router.post("/cases/{case_id}/velocity-analyze", response_model=VelocityAnalysisResponse, summary="Analyze High-Velocity Movement for Case")
def analyze_case_velocity(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Analyze rapid transaction velocity patterns across fund flow traces attached to a case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    trace_run = (
        db.query(TraceRun)
        .filter(TraceRun.case_id == case_id)
        .order_by(TraceRun.started_at.desc())
        .first()
    )

    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace runs found for case '{case_id}'. Execute a trace first.",
        )

    service = VelocityService(db)
    return service.analyze_trace_id(trace_run.trace_id, case_id=case_id)


@router.get("/cases/{case_id}/velocity-alerts", response_model=List[VelocityAlert], summary="Get Case Velocity Alerts")
def get_case_velocity_alerts(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve all high-velocity movement alerts triggered for a case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    alerts_db = (
        db.query(Alert)
        .filter(Alert.case_id == case_id, Alert.alert_type == "HIGH_VELOCITY_MOVEMENT")
        .all()
    )

    result: List[VelocityAlert] = []
    for a in alerts_db:
        m = a.metrics or {}
        result.append(
            VelocityAlert(
                alert_id=str(a.id),
                trace_id=str(m.get("trace_id", "") if m else ""),
                case_id=a.case_id,
                alert_type=a.alert_type,
                severity=a.severity,
                velocity_score=float(m.get("velocity_score", 0.0)),
                transfer_count=int(m.get("transfer_count", 0)),
                total_amount=float(m.get("total_amount", 0.0)),
                duration_seconds=float(m.get("duration_seconds", 0.0)),
                minimum_delta_t=float(m.get("minimum_delta_t", 0.0)),
                average_delta_t=float(m.get("average_delta_t", 0.0)),
                maximum_delta_t=float(m.get("maximum_delta_t", 0.0)),
                unique_recipients=int(m.get("unique_recipients", 0)),
                downstream_hops=int(m.get("downstream_hops", 0)),
                supporting_transactions=a.supporting_tx_hashes or [],
                supporting_wallets=a.supporting_wallets or [],
                reason_codes=m.get("reason_codes", []),
                score_components=m.get("score_components", {}),
                explanation=a.explanation,
                analyzed_at=a.created_at,
            )
        )
    return result


@router.get("/cases/{case_id}/typologies", response_model=TypologyAnalysisResponse, summary="Get Case Transaction Typologies")
def get_case_typologies(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Detect and retrieve transaction typology structural patterns (Fan-Out, Fan-In, Consolidation, Rapid Peel, VASP Convergence) for a case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    trace_run = (
        db.query(TraceRun)
        .filter(TraceRun.case_id == case_id)
        .order_by(TraceRun.started_at.desc())
        .first()
    )

    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace runs found for case '{case_id}'.",
        )

    service = TypologyService(db)
    return service.analyze_trace_id(trace_run.trace_id, case_id=case_id)


@router.get("/cases/{case_id}/risk", response_model=RiskIndicatorResponse, summary="Get Case Transaction-Flow Risk Indicator")
def get_case_risk_indicator(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Compute transparent Transaction-Flow Risk Indicator (0-100) combining velocity, typologies, retention, and false positive safety rules.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    trace_run = (
        db.query(TraceRun)
        .filter(TraceRun.case_id == case_id)
        .order_by(TraceRun.started_at.desc())
        .first()
    )

    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace runs found for case '{case_id}'.",
        )

    service = RiskService(db)
    return service.analyze_trace_id(trace_run.trace_id, case_id=case_id)


@router.post("/trace/{trace_id}/analyze-patterns", summary="Analyze All Structural & Velocity Patterns for Trace ID")
def analyze_trace_patterns(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Comprehensive pattern analysis on a trace execution: velocity alerts, typologies, and risk indicator.
    """
    trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace run '{trace_id}' not found.",
        )

    v_service = VelocityService(db)
    t_service = TypologyService(db)
    r_service = RiskService(db)

    velocity_res = v_service.analyze_trace_id(trace_id)
    typology_res = t_service.analyze_trace_id(trace_id)
    risk_res = r_service.analyze_trace_id(trace_id)

    return {
        "trace_id": trace_id,
        "case_id": trace_run.case_id,
        "starting_wallet": trace_run.starting_wallet,
        "velocity_analysis": velocity_res,
        "typology_analysis": typology_res,
        "risk_indicator": risk_res,
    }


@router.get("/trace/{trace_id}/alerts", response_model=List[VelocityAlert], summary="Get Velocity Alerts by Trace ID")
def get_trace_alerts(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve velocity alerts generated for a specific trace ID.
    """
    v_service = VelocityService(db)
    res = v_service.analyze_trace_id(trace_id)
    return res.alerts


@router.get("/trace/{trace_id}/typologies", response_model=TypologyAnalysisResponse, summary="Get Typologies by Trace ID")
def get_trace_typologies(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve detected transaction typologies for a specific trace ID.
    """
    t_service = TypologyService(db)
    return t_service.analyze_trace_id(trace_id)
