import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TracePath, TraceEdge
from app.models.alert import Alert
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.velocity import (
    VelocityAlert,
    VelocityAnalysisResponse,
    RollingWindowMetric,
)
from app.velocity.detector import VelocityDetector
from app.velocity.scorer import VelocityScorer
from app.velocity.evidence import VelocityEvidenceBuilder

logger = logging.getLogger("specter.velocity.service")


class VelocityService:
    """
    Service orchestrating High-Velocity Movement analysis over multi-hop fund-flow graphs.
    Computes time deltas, rolling time window metrics, velocity scores, and generates structured alerts.
    """

    def __init__(self, db: Session):
        self.db = db
        self.detector = VelocityDetector()
        self.scorer = VelocityScorer()
        self.evidence_builder = VelocityEvidenceBuilder()

    def analyze_trace(
        self,
        trace_result: TraceResultResponse,
        case_id: Optional[str] = None,
        velocity_threshold_seconds: float = 300.0,
    ) -> VelocityAnalysisResponse:
        """Perform velocity analysis on a TraceResultResponse."""
        eff_case_id = case_id or trace_result.case_id

        # 1. Compute velocity metrics across graph transfers
        metrics = self.detector.analyze_trace_velocity(trace_result)

        # 2. Compute Velocity Alert Score (0-100), severity, reason codes & component scores
        score, severity, reason_codes, score_components = self.scorer.score_velocity(
            metrics=metrics,
            velocity_threshold_seconds=velocity_threshold_seconds,
        )

        # 3. Formulate explanation
        explanation = self.evidence_builder.generate_explanation(
            velocity_score=score,
            severity=severity,
            metrics=metrics,
            reason_codes=reason_codes,
        )

        alerts: List[VelocityAlert] = []
        has_high_velocity = (score >= 40.0 and metrics.transfer_count >= 2)

        if has_high_velocity:
            alert_id = str(uuid.uuid4())
            val_alert = VelocityAlert(
                alert_id=alert_id,
                trace_id=trace_result.trace_id,
                case_id=eff_case_id,
                alert_type="HIGH_VELOCITY_MOVEMENT",
                severity=severity,
                velocity_score=score,
                transfer_count=metrics.transfer_count,
                total_amount=metrics.total_amount,
                duration_seconds=metrics.duration_seconds,
                minimum_delta_t=metrics.minimum_delta_t,
                average_delta_t=metrics.average_delta_t,
                maximum_delta_t=metrics.maximum_delta_t,
                unique_recipients=metrics.unique_recipients,
                downstream_hops=metrics.downstream_hops,
                supporting_transactions=metrics.supporting_transactions,
                supporting_wallets=metrics.supporting_wallets,
                reason_codes=reason_codes,
                rolling_windows=metrics.rolling_windows,
                score_components=score_components,
                explanation=explanation,
                initial_transfer_amount=metrics.initial_transfer_amount,
                downstream_activity_amount=metrics.downstream_activity_amount,
                analyzed_at=datetime.now(timezone.utc),
            )
            alerts.append(val_alert)

            # Persist Alert record into DB if case_id present
            if eff_case_id:
                db_alert = Alert(
                    case_id=eff_case_id,
                    alert_type="HIGH_VELOCITY_MOVEMENT",
                    severity=severity,
                    explanation=explanation,
                    metrics={
                        "velocity_score": score,
                        "transfer_count": metrics.transfer_count,
                        "total_amount": metrics.total_amount,
                        "initial_transfer_amount": metrics.initial_transfer_amount,
                        "downstream_activity_amount": metrics.downstream_activity_amount,
                        "duration_seconds": metrics.duration_seconds,
                        "minimum_delta_t": metrics.minimum_delta_t,
                        "average_delta_t": metrics.average_delta_t,
                        "reason_codes": reason_codes,
                    },
                    supporting_tx_hashes=metrics.supporting_transactions,
                    supporting_wallets=metrics.supporting_wallets,
                )
                self.db.add(db_alert)
                self.db.commit()

        status = "RESOLVED_ALERT" if has_high_velocity else "NO_HIGH_VELOCITY_PATTERN_DETECTED"

        return VelocityAnalysisResponse(
            trace_id=trace_result.trace_id,
            case_id=eff_case_id,
            starting_wallet=trace_result.starting_wallet,
            chain=trace_result.chain,
            asset=trace_result.asset,
            has_high_velocity_pattern=has_high_velocity,
            status=status,
            summary=explanation,
            alerts=alerts,
            rolling_windows=metrics.rolling_windows,
            metrics={
                "transfer_count": metrics.transfer_count,
                "total_amount": metrics.total_amount,
                "initial_transfer_amount": metrics.initial_transfer_amount,
                "downstream_activity_amount": metrics.downstream_activity_amount,
                "duration_seconds": metrics.duration_seconds,
                "minimum_delta_t": metrics.minimum_delta_t,
                "average_delta_t": metrics.average_delta_t,
                "maximum_delta_t": metrics.maximum_delta_t,
                "unique_recipients": metrics.unique_recipients,
                "downstream_hops": metrics.downstream_hops,
            },
        )

    def analyze_trace_id(
        self,
        trace_id: str,
        case_id: Optional[str] = None,
        velocity_threshold_seconds: float = 300.0,
    ) -> VelocityAnalysisResponse:
        """Fetch trace run from DB and analyze high-velocity patterns."""
        trace_run = self.db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
        if not trace_run:
            raise ValueError(f"Trace run '{trace_id}' not found.")

        trace_result = self._reconstruct_trace_result(trace_run)
        return self.analyze_trace(
            trace_result=trace_result,
            case_id=case_id or trace_run.case_id,
            velocity_threshold_seconds=velocity_threshold_seconds,
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
