import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TracePath, TraceEdge
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.typology import TypologyAnalysisResponse, TypologyResult
from app.typologies.detector import TypologyDetector
from app.typologies.scorer import TypologyScorer
from app.typologies.evidence import TypologyEvidenceBuilder

logger = logging.getLogger("specter.typologies.service")


class TypologyService:
    """
    Service orchestrating Transaction Typology detection across multi-hop fund-flow graphs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.detector = TypologyDetector(db)
        self.scorer = TypologyScorer()
        self.evidence_builder = TypologyEvidenceBuilder()

    def analyze_trace(
        self,
        trace_result: TraceResultResponse,
        case_id: Optional[str] = None,
    ) -> TypologyAnalysisResponse:
        """Run typology detection rules on a TraceResultResponse."""
        eff_case_id = case_id or trace_result.case_id

        # 1. Detect typologies
        typologies = self.detector.analyze_typologies(trace_result)

        # 2. Formulate summary
        summary = self.evidence_builder.generate_summary(
            typologies=typologies,
            starting_wallet=trace_result.starting_wallet,
        )

        status = "TYPOLOGIES_DETECTED" if typologies else "NO_TYPOLOGIES_DETECTED"

        return TypologyAnalysisResponse(
            trace_id=trace_result.trace_id,
            case_id=eff_case_id,
            starting_wallet=trace_result.starting_wallet,
            chain=trace_result.chain,
            asset=trace_result.asset,
            status=status,
            summary=summary,
            typologies=typologies,
            analyzed_at=datetime.now(timezone.utc),
        )

    def analyze_trace_id(
        self,
        trace_id: str,
        case_id: Optional[str] = None,
    ) -> TypologyAnalysisResponse:
        """Fetch trace run from DB and analyze transaction typologies."""
        trace_run = self.db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
        if not trace_run:
            raise ValueError(f"Trace run '{trace_id}' not found.")

        trace_result = self._reconstruct_trace_result(trace_run)
        return self.analyze_trace(
            trace_result=trace_result,
            case_id=case_id or trace_run.case_id,
        )

    def _reconstruct_trace_result(self, trace_run: TraceRun) -> TraceResultResponse:
        paths_db = self.db.query(TracePath).filter(TracePath.trace_id == trace_run.trace_id).all()
        edges_db = self.db.query(TraceEdge).filter(TraceEdge.trace_id == trace_run.trace_id).all()

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

            paths_detail.append(
                TracePathDetail(
                    path_id=p.path_id,
                    wallet_sequence=p.wallet_sequence,
                    hop_count=p.hop_count,
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
