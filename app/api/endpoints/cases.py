from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.case import Case
from app.schemas.case import CaseCreate, CaseRead, CaseDetailRead, CaseUpdate

router = APIRouter()


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED, summary="Create Investigation Case")
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)):
    """
    Create a new persistent investigation case for a reported suspicious wallet address.
    """
    case = Case(
        investigator_id=case_in.investigator_id,
        reported_wallet=case_in.reported_wallet.strip(),
        chain=case_in.chain.upper().strip(),
        asset=case_in.asset.upper().strip(),
        description=case_in.description,
        status="ACTIVE",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("", response_model=List[CaseRead], summary="List Investigation Cases")
def list_cases(
    chain: Optional[str] = Query(None, description="Filter by blockchain"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List investigation cases with optional chain and status filtering.
    """
    query = db.query(Case)
    if chain:
        query = query.filter(Case.chain == chain.upper().strip())
    if status_filter:
        query = query.filter(Case.status == status_filter.upper().strip())
    
    cases = query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()
    return cases


@router.get("/{case_id}", response_model=CaseDetailRead, summary="Get Case Details")
def get_case(case_id: str, db: Session = Depends(get_db)):
    """
    Retrieve full details and counts for a specific investigation case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found."
        )
    
    detail = CaseDetailRead(
        case_id=case.case_id,
        investigator_id=case.investigator_id,
        reported_wallet=case.reported_wallet,
        chain=case.chain,
        asset=case.asset,
        status=case.status,
        description=case.description,
        created_at=case.created_at,
        updated_at=case.updated_at,
        transaction_count=len(case.transactions),
        evidence_count=len(case.evidence_items),
        alert_count=len(case.alerts),
        vasp_candidate_count=len(case.vasp_candidates),
    )
    return detail


@router.patch("/{case_id}", response_model=CaseRead, summary="Update Case Status / Notes")
def update_case(case_id: str, case_in: CaseUpdate, db: Session = Depends(get_db)):
    """
    Update status or notes for an ongoing investigation case.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found."
        )
    
    if case_in.status is not None:
        case.status = case_in.status.upper().strip()
    if case_in.description is not None:
        case.description = case_in.description
        
    db.commit()
    db.refresh(case)
    return case
