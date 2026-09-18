import logging
from typing import List, Dict, Any, Optional
from app.vasp.scorer import ScoredCandidate, SCORING_MODEL_VERSION

logger = logging.getLogger("specter.vasp.evidence")


class VASPEvidenceBuilder:
    """
    Constructs comprehensive machine-readable and human-readable evidence ledgers
    for VASP attribution evaluations.
    """

    def build_evidence_ledger(self, candidate: ScoredCandidate) -> Dict[str, Any]:
        """Build a detailed audit ledger for a scored VASP candidate."""
        matched = candidate.matched_candidate

        ledger = {
            "candidate_name": candidate.candidate_name,
            "entity_role": candidate.entity_role,
            "endpoint_address": candidate.endpoint_address,
            "chain": candidate.chain,
            "hop_distance": candidate.endpoint_hop_distance,
            "match_position": candidate.match_position,
            "is_terminal_endpoint": candidate.is_terminal_endpoint,
            "attribution_type": candidate.attribution_type,
            "scoring_model_version": SCORING_MODEL_VERSION,
            "metrics": {
                "source_confidence": candidate.source_confidence,
                "attribution_confidence": candidate.attribution_confidence,
                "confidence_band": candidate.confidence_band,
                "value_transferred": candidate.value_transferred,
                "value_retention_percent": candidate.value_retention_percent,
                "temporal_proximity_seconds": candidate.temporal_proximity_seconds,
                "path_convergence_count": candidate.path_convergence_count,
            },
            "score_breakdown": candidate.score_components,
            "evidence_statements": candidate.evidence_summary,
            "why_this_vasp": candidate.why_this_vasp,
            "path_sequence": candidate.path_sequence,
            "supporting_transactions": candidate.supporting_transactions,
            "supporting_wallets": candidate.supporting_wallets,
            "source_provenance": candidate.source_metadata,
            "flow_summary": {
                "paths_count": len(matched.paths_involved),
                "max_value_retention_pct": max([p.value_retention_percent for p in matched.paths_involved]) if matched.paths_involved else 0.0,
                "min_elapsed_seconds": min([p.elapsed_time_seconds for p in matched.paths_involved]) if matched.paths_involved else 0.0,
            },
            "disclaimer": (
                "Analytical attribution based on on-chain transfer topology and documented source intelligence. "
                "Does not prove legal ownership or definitive identity of private individuals controlling private keys."
            ),
        }

        return ledger

    def generate_explanation(
        self,
        top_candidate: Optional[ScoredCandidate],
        total_candidates_found: int,
        starting_wallet: str,
        wallets_traced_count: int = 0,
        transactions_traced_count: int = 0,
        threshold: float = 70.0,
        status: str = "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED",
    ) -> str:
        """
        Generate a clear, conservative, evidence-based analytical explanation statement.
        Never claims ownership proven, legal certainty, or automatic person identification.
        """
        if status == "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED" or not top_candidate or not top_candidate.is_terminal_endpoint or top_candidate.attribution_confidence < threshold:
            reason_detail = ""
            if top_candidate and not top_candidate.is_terminal_endpoint:
                reason_detail = f" Candidate '{top_candidate.candidate_name}' matched only as an intermediate hop, not a terminal custodial endpoint."
            elif top_candidate and top_candidate.attribution_confidence < threshold:
                reason_detail = f" Top candidate '{top_candidate.candidate_name}' achieved confidence {top_candidate.attribution_confidence:.1f}%, which is below the high-confidence threshold ({threshold:.0f}%)."

            return (
                f"NO HIGH-CONFIDENCE VASP IDENTIFIED for target wallet {starting_wallet}. "
                f"The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP.{reason_detail} "
                f"Evaluated {total_candidates_found} candidate entity/entities across {wallets_traced_count} wallet(s) "
                f"and {transactions_traced_count} transaction(s). This is a valid investigation result."
            )

        cb = top_candidate.confidence_band
        score = top_candidate.attribution_confidence
        name = top_candidate.candidate_name
        endpoint = top_candidate.endpoint_address
        hops = top_candidate.endpoint_hop_distance
        attr_type = top_candidate.attribution_type
        role = top_candidate.entity_role

        return (
            f"Likely VASP attribution identified candidate '{name}' ({role}) at terminal endpoint address {endpoint} "
            f"with {cb} confidence (Score: {score:.1f}/100, {hops}-hop distance, Classification: {attr_type}). "
            f"Analysis indicates evidence-backed fund flow continuity to a known VASP operational address. "
            f"Evaluated against model version {SCORING_MODEL_VERSION} using {len(top_candidate.supporting_transactions)} supporting transaction(s); "
            f"does not constitute legal proof of beneficial ownership or custodial control."
        )
