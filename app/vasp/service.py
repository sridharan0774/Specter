import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TracePath, TraceEdge
from app.models.vasp import VASPAttribution, VASPCandidate, VASPRecord
from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.vasp import (
    VASPAttributionCandidate,
    VASPAttributionResponse,
    VASPCandidateScore,
)
from app.core.config import settings
from app.vasp.repository import VASPRepository
from app.vasp.matcher import VASPMatcher
from app.vasp.scorer import VASPScorer, SCORING_MODEL_VERSION
from app.vasp.evidence import VASPEvidenceBuilder

logger = logging.getLogger("specter.vasp.service")


class VASPService:
    """
    Core service orchestrating source-backed VASP attribution analysis across multi-hop trace graphs.
    Enforces conservative evidence policies, dual confidence metrics, explicit source provenance,
    and returns 'NO HIGH-CONFIDENCE VASP IDENTIFIED' when confidence is insufficient.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = VASPRepository(db)
        self.matcher = VASPMatcher(self.repository)
        self.scorer = VASPScorer()
        self.evidence_builder = VASPEvidenceBuilder()

    def resolve_from_trace_result(
        self,
        trace_result: TraceResultResponse,
        case_id: Optional[str] = None,
    ) -> VASPAttributionResponse:
        """
        Perform analytical VASP attribution resolution on an in-memory TraceResultResponse.
        """
        # Ensure public intelligence seed records exist in DB
        self.repository.seed_known_public_vasps()

        starting_wallet = trace_result.starting_wallet.strip()
        eff_case_id = case_id or trace_result.case_id

        # 1. Match candidate endpoints across the trace graph
        matched_candidates = self.matcher.find_candidates(
            trace_result=trace_result,
            starting_wallet=starting_wallet,
        )

        # 2. Score each candidate
        scored_candidates = [self.scorer.score_candidate(m) for m in matched_candidates]

        # 3. Candidate ranking:
        #    Primary: Terminal endpoints strictly prioritized over intermediate associations
        #    Secondary: Highest attribution confidence score
        #    Tertiary: Nearest hop distance (nearest VASP)
        #    Quaternary: Highest value transferred
        scored_candidates.sort(
            key=lambda c: (
                1 if c.is_terminal_endpoint else 0,
                c.attribution_confidence,
                -c.endpoint_hop_distance,
                c.value_transferred,
            ),
            reverse=True,
        )

        # 4. Filter and assign ranks
        attribution_candidates: List[VASPAttributionCandidate] = []
        for rank, c in enumerate(scored_candidates, start=1):
            relevance_reasons = [f"✓ {stmt}" if not stmt.startswith("✓") else stmt for stmt in (c.why_this_vasp or c.evidence_summary)]

            attribution_candidates.append(
                VASPAttributionCandidate(
                    rank=rank,
                    candidate_name=c.candidate_name,
                    entity_role=c.entity_role,
                    endpoint_address=c.endpoint_address,
                    chain=c.chain,
                    endpoint_hop_distance=c.endpoint_hop_distance,
                    match_position=c.match_position,
                    is_terminal_endpoint=c.is_terminal_endpoint,
                    attribution_type=c.attribution_type,
                    source_confidence=c.source_confidence,
                    attribution_confidence=c.attribution_confidence,
                    confidence_band=c.confidence_band,
                    value_transferred=c.value_transferred,
                    value_retention_percent=c.value_retention_percent,
                    temporal_proximity_seconds=c.temporal_proximity_seconds,
                    path_convergence_count=c.path_convergence_count,
                    score_components=c.score_components,
                    evidence_summary=c.evidence_summary,
                    why_this_vasp=c.why_this_vasp,
                    supporting_transactions=c.supporting_transactions,
                    supporting_wallets=c.supporting_wallets,
                    path_sequence=c.path_sequence,
                    source_metadata=c.source_metadata,
                    matched_relevance_reasons=relevance_reasons,
                )
            )

        # 5. Evaluate overall attribution status & conservative threshold:
        #    Must meet high confidence threshold AND be a direct/terminal endpoint!
        high_conf_threshold = getattr(settings, "VASP_HIGH_CONFIDENCE_THRESHOLD", 70.0)
        top_scored = scored_candidates[0] if scored_candidates else None
        
        if top_scored and top_scored.is_terminal_endpoint and top_scored.attribution_confidence >= high_conf_threshold:
            status = "RESOLVED"
            negative_reason = None
        else:
            status = "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"
            if not top_scored:
                negative_reason = "The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP. All traced paths terminated at unclassified addresses."
            elif not top_scored.is_terminal_endpoint:
                negative_reason = f"Candidate '{top_scored.candidate_name}' matched only as an intermediate hop along the path, not as a terminal custodial endpoint. Funds exited downstream."
            else:
                negative_reason = f"Candidate '{top_scored.candidate_name}' achieved an attribution confidence of {top_scored.attribution_confidence:.1f}%, which is below the required high-confidence threshold of {high_conf_threshold:.0f}%."

        explanation = self.evidence_builder.generate_explanation(
            top_candidate=top_scored,
            total_candidates_found=len(scored_candidates),
            starting_wallet=starting_wallet,
            wallets_traced_count=trace_result.total_wallets_discovered,
            transactions_traced_count=trace_result.total_transactions_analyzed,
            threshold=high_conf_threshold,
            status=status,
        )

        attribution_id = str(uuid.uuid4())
        evaluated_at = datetime.now(timezone.utc)

        # 6. Persist attribution records in database if resolved
        if top_scored and status == "RESOLVED":
            attribution_record = VASPAttribution(
                attribution_id=attribution_id,
                case_id=eff_case_id,
                trace_id=trace_result.trace_id,
                candidate_name=top_scored.candidate_name,
                candidate_entity_id=getattr(top_scored, "candidate_entity_id", None),
                entity_role=top_scored.entity_role,
                endpoint_address=top_scored.endpoint_address,
                chain=top_scored.chain,
                endpoint_hop_distance=top_scored.endpoint_hop_distance,
                match_position=top_scored.match_position,
                is_terminal_endpoint=1 if top_scored.is_terminal_endpoint else 0,
                value_transferred=top_scored.value_transferred,
                value_retention_percent=top_scored.value_retention_percent,
                temporal_proximity_seconds=top_scored.temporal_proximity_seconds,
                path_convergence_count=top_scored.path_convergence_count,
                attribution_type=top_scored.attribution_type,
                source_confidence=top_scored.source_confidence,
                attribution_confidence=top_scored.attribution_confidence,
                confidence_band=top_scored.confidence_band,
                score_components=top_scored.score_components,
                evidence_summary={"statements": top_scored.evidence_summary, "why_this_vasp": top_scored.why_this_vasp},
                supporting_transactions=top_scored.supporting_transactions,
                supporting_wallets=top_scored.supporting_wallets,
                scoring_model_version=SCORING_MODEL_VERSION,
                evaluated_at=evaluated_at,
            )
            self.db.add(attribution_record)

            # Support legacy VASPCandidate table if case_id present
            if eff_case_id:
                legacy_candidate = VASPCandidate(
                    case_id=eff_case_id,
                    candidate_vasp=top_scored.candidate_name,
                    confidence_score=top_scored.attribution_confidence / 100.0,
                    component_scores=top_scored.score_components,
                    supporting_evidence=top_scored.evidence_summary,
                    transaction_path=top_scored.supporting_transactions,
                    relevant_wallets=top_scored.supporting_wallets,
                    source_labels=[top_scored.source_metadata],
                )
                self.db.add(legacy_candidate)

            self.db.commit()

        known_matches = [c.endpoint_address for c in scored_candidates]

        return VASPAttributionResponse(
            attribution_id=attribution_id,
            trace_id=trace_result.trace_id,
            case_id=eff_case_id,
            starting_wallet=starting_wallet,
            target_wallet=starting_wallet,
            chain=trace_result.chain,
            asset=trace_result.asset,
            status=status,
            resolution_status=status,
            has_high_confidence_match=(status == "RESOLVED"),
            wallets_traced_count=trace_result.total_wallets_discovered,
            transactions_traced_count=trace_result.total_transactions_analyzed,
            candidates_considered_count=len(scored_candidates),
            known_endpoint_matches=known_matches,
            negative_reason=negative_reason,
            explanation=explanation,
            scoring_model_version=SCORING_MODEL_VERSION,
            evaluated_at=evaluated_at,
            candidates=attribution_candidates,
        )

    def resolve_from_trace_id(
        self,
        trace_id: str,
        case_id: Optional[str] = None,
    ) -> VASPAttributionResponse:
        """
        Fetch stored trace run from database and resolve VASP attribution.
        """
        trace_run = self.db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
        if not trace_run:
            raise ValueError(f"Trace run '{trace_id}' not found.")

        trace_result = self._reconstruct_trace_result(trace_run)
        return self.resolve_from_trace_result(trace_result, case_id=case_id or trace_run.case_id)

    def _reconstruct_trace_result(self, trace_run: TraceRun) -> TraceResultResponse:
        """Reconstruct TraceResultResponse from DB model records."""
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
