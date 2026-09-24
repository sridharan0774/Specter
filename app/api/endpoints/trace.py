from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.case import Case
from app.models.trace import TraceRun, TracePath, TraceEdge
from app.schemas.trace import TraceRequest, TraceResultResponse, TracePathDetail, TraceHopItem
from app.tracing.engine import TraceEngine

router = APIRouter()


@router.post("/cases/{case_id}/trace", response_model=TraceResultResponse, summary="Execute Multi-Hop Fund Trace for Case")
async def execute_case_trace(
    case_id: str,
    request: TraceRequest,
    db: Session = Depends(get_db),
):
    """
    Execute real multi-hop transaction tracing starting from a wallet associated with a case.
    Traverses outgoing transactions using TRON live network data up to max_hops depth.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found.",
        )

    # Use starting wallet from request, or default to case's reported wallet
    if not request.starting_wallet or request.starting_wallet == "string":
        request.starting_wallet = case.reported_wallet

    engine = TraceEngine(db=db)
    result = await engine.execute_trace(request=request, case_id=case_id)
    return result


@router.post("/trace", response_model=TraceResultResponse, summary="Execute Standalone Multi-Hop Fund Trace")
async def execute_standalone_trace(
    request: TraceRequest,
    db: Session = Depends(get_db),
):
    """
    Execute multi-hop transaction flow tracing on a target wallet address without a case container.
    """
    engine = TraceEngine(db=db)
    result = await engine.execute_trace(request=request, case_id=None)
    return result


@router.get("/cases/{case_id}/traces/{trace_id}", response_model=TraceResultResponse, summary="Get Case Trace Results")
def get_case_trace(
    case_id: str,
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve stored trace results, paths, and graph metrics for a specific case trace execution.
    """
    trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id, TraceRun.case_id == case_id).first()
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace run '{trace_id}' for case '{case_id}' not found.",
        )

    return _build_trace_response(db, trace_run)


@router.get("/trace/{trace_id}", response_model=TraceResultResponse, summary="Get Trace Results by ID")
def get_trace_by_id(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve stored trace execution results by trace ID.
    """
    trace_run = db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
    if not trace_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace run '{trace_id}' not found.",
        )

    return _build_trace_response(db, trace_run)


def _build_trace_response(db: Session, trace_run: TraceRun) -> TraceResultResponse:
    """Helper to reconstruct TraceResultResponse from DB models."""
    paths_db = db.query(TracePath).filter(TracePath.trace_id == trace_run.trace_id).all()
    edges_db = db.query(TraceEdge).filter(TraceEdge.trace_id == trace_run.trace_id).all()

    # Create mapping of tx_hash to edge model
    edge_map = {e.tx_hash: e for e in edges_db}

    paths_detail: List[TracePathDetail] = []
    for p in paths_db:
        hops: List[TraceHopItem] = []
        edge_hashes = p.edge_sequence or []
        for idx, tx_hash in enumerate(edge_hashes, start=1):
            edge = edge_map.get(tx_hash)
            if edge:
                hops.append(
                    TraceHopItem(
                        hop_number=idx,
                        from_address=edge.from_wallet,
                        to_address=edge.to_wallet,
                        tx_hash=edge.tx_hash,
                        asset=edge.asset,
                        amount=edge.amount,
                        timestamp=edge.timestamp,
                        block_number=None,
                        delta_t_seconds=edge.delta_t_seconds,
                        explorer_url=edge.explorer_url,
                    )
                )

        if hops:
            wallet_seq = [hops[0].from_address] + [h.to_address for h in hops]
            hop_cnt = len(hops)
        elif p.wallet_sequence:
            wallet_seq = p.wallet_sequence
            hop_cnt = p.hop_count if p.hop_count is not None else max(0, len(wallet_seq) - 1)
        else:
            wallet_seq = []
            hop_cnt = 0

        paths_detail.append(
            TracePathDetail(
                path_id=p.path_id,
                wallet_sequence=wallet_seq,
                hop_count=hop_cnt,
                initial_amount=p.initial_amount,
                final_amount=p.final_amount,
                value_retention_percent=p.value_retention_percent,
                elapsed_time_seconds=p.elapsed_time_seconds,
                relevance_score=p.relevance_score,
                relevance_explanation=p.relevance_explanation,
                cycle_detected=p.cycle_detected,
                metrics=p.metrics or {},
                hops=hops,
            )
        )


    return TraceResultResponse(
        trace_id=trace_run.trace_id,
        case_id=trace_run.case_id,
        starting_wallet=trace_run.starting_wallet,
        chain=trace_run.chain,
        asset=trace_run.asset,
        status=trace_run.status,
        truncated=trace_run.truncated,
        truncation_reason=trace_run.truncation_reason,
        total_wallets_discovered=trace_run.total_wallets_discovered,
        total_transactions_analyzed=trace_run.total_transactions_analyzed,
        total_edges_discovered=trace_run.total_edges_discovered,
        total_paths_found=trace_run.total_paths_found,
        processing_time_seconds=trace_run.processing_time_seconds,
        started_at=trace_run.started_at,
        completed_at=trace_run.completed_at,
        paths=paths_detail,
    )
