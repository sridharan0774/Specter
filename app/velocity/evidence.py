import logging
from typing import Dict, Any, List
from app.velocity.detector import VelocityMetrics

logger = logging.getLogger("specter.velocity.evidence")


class VelocityEvidenceBuilder:
    """
    Constructs explainable evidence summaries and analytical explanations
    for high-velocity movement alerts.
    """

    def generate_explanation(
        self,
        velocity_score: float,
        severity: str,
        metrics: VelocityMetrics,
        reason_codes: List[str],
    ) -> str:
        """Formulate a clear human and machine readable summary statement."""
        if metrics.minimum_delta_t is not None:
            min_delta_str = f"{metrics.minimum_delta_t:.1f}s"
        else:
            min_delta_str = "N/A (insufficient sequential transfers)"

        if metrics.average_delta_t is not None:
            avg_delta_str = f"{metrics.average_delta_t:.1f}s"
        else:
            avg_delta_str = "N/A"

        if velocity_score < 40.0 or metrics.transfer_count <= 1:
            if metrics.transfer_count <= 1:
                timing_context = "single transfer"
            else:
                timing_context = f"{metrics.duration_seconds:.1f}s duration"

            return (
                f"NO HIGH-VELOCITY PATTERN DETECTED. Analyzed {metrics.transfer_count} transfer(s) "
                f"({timing_context}). Minimum delta_t: {min_delta_str}, "
                f"average delta_t: {avg_delta_str}. Velocity score ({velocity_score:.1f}/100) below threshold."
            )

        duration_str = self._format_duration(metrics.duration_seconds)
        reasons_str = ", ".join(reason_codes) if reason_codes else "RAPID_TRANSFER_SEQUENCE"

        initial_amt = getattr(metrics, "initial_transfer_amount", 0.0)
        downstream_amt = getattr(metrics, "downstream_activity_amount", 0.0)
        if downstream_amt > 0:
            amount_detail = (
                f"INITIAL OBSERVED TRANSFER: ${initial_amt:,.2f} USDT, "
                f"DOWNSTREAM OBSERVED ACTIVITY: ${downstream_amt:,.2f} USDT across {metrics.transfer_count} transfers"
            )
        else:
            amount_detail = f"Observed {metrics.transfer_count} transfers moving ${metrics.total_amount:,.2f} USDT"

        return (
            f"HIGH-VELOCITY MOVEMENT DETECTED [{severity} Severity, Score: {velocity_score:.1f}/100]. "
            f"{amount_detail} across {duration_str} "
            f"({metrics.unique_recipients} unique recipient(s), {metrics.downstream_hops} downstream hop(s)). "
            f"Minimum delta_t: {min_delta_str}, average delta_t: {avg_delta_str}. "
            f"Trigger reasons: {reasons_str}."
        )

    def build_evidence_payload(
        self,
        metrics: VelocityMetrics,
        velocity_score: float,
        score_components: Dict[str, float],
    ) -> Dict[str, Any]:
        """Build machine readable evidence dictionary connecting alert to underlying transactions."""
        return {
            "metrics": {
                "transfer_count": metrics.transfer_count,
                "total_amount": metrics.total_amount,
                "duration_seconds": metrics.duration_seconds,
                "minimum_delta_t": metrics.minimum_delta_t,
                "average_delta_t": metrics.average_delta_t,
                "maximum_delta_t": metrics.maximum_delta_t,
                "unique_recipients": metrics.unique_recipients,
                "downstream_hops": metrics.downstream_hops,
            },
            "velocity_score": velocity_score,
            "score_components": score_components,
            "supporting_transactions": metrics.supporting_transactions,
            "supporting_wallets": metrics.supporting_wallets,
            "delta_ts": metrics.delta_ts,
        }

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m}m {s}s"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h {m}m"
