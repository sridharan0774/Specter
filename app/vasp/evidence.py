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
            "endpoint_address": candidate.endpoint_address,
            "chain": candidate.chain,
            "hop_distance": candidate.endpoint_hop_distance,
            "attribution_type": candidate.attribution_type,
            "scoring_model_version": SCORING_MODEL_VERSION,
            "metrics": {
                "source_confidence": candidate.source_confidence,
                "attribution_confidence": candidate.attribution_confidence,
                "confidence_band": candidate.confidence_band,
            },
            "score_breakdown": candidate.score_components,
            "evidence_statements": candidate.evidence_summary,
            "path_sequence": candidate.path_sequence,
            "supporting_transactions": candidate.supporting_transactions,
            "supporting_wallets": candidate.supporting_wallets,
            "source_provenance": candidate.source_metadata,
            "flow_summary": {
                "paths_count": len(matched.paths_involved),
                "max_value_retention_pct": max([p.value_retention_percent for p in matched.paths_involved]) if matched.paths_involved else 0.0,
                "min_elapsed_seconds": min([p.elapsed_time_seconds for p in matched.paths_involved]) if matched.paths_involved else 0.0,
            },
        }

        return ledger

    def generate_explanation(
        self,
        top_candidate: Optional[ScoredCandidate],
        total_candidates_found: int,
        starting_wallet: str,
    ) -> str:
        """
        Generate a clear, conservative, analytical explanation statement.
        If no candidate meets the threshold (confidence < 40 or no candidates),
        returns explicit 'NO HIGH-CONFIDENCE VASP IDENTIFIED'.
        """
        if not top_candidate or top_candidate.confidence_band == "INSUFFICIENT":
            return (
                f"NO HIGH-CONFIDENCE VASP IDENTIFIED for starting wallet {starting_wallet}. "
                f"Evaluated {total_candidates_found} candidate endpoint(s) across fund flow paths, "
                f"but none exceeded the required minimum confidence threshold (Score >= 40.0)."
            )

        cb = top_candidate.confidence_band
        score = top_candidate.attribution_confidence
        name = top_candidate.candidate_name
        endpoint = top_candidate.endpoint_address
        hops = top_candidate.endpoint_hop_distance
        attr_type = top_candidate.attribution_type

        return (
            f"VASP Attribution identified candidate '{name}' at endpoint address {endpoint} "
            f"with {cb} confidence (Score: {score}/100, {hops}-hop distance, Classification: {attr_type}). "
            f"Evaluated against model version {SCORING_MODEL_VERSION} using {len(top_candidate.supporting_transactions)} supporting transaction(s)."
        )
