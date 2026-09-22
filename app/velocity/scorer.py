import logging
from typing import Dict, Any, List, Tuple
from app.velocity.detector import VelocityMetrics

logger = logging.getLogger("specter.velocity.scorer")


class VelocityScorer:
    """
    Calculates a transparent Velocity Alert Score (0-100), severity rating,
    component breakdown, and reason codes for high-velocity transfer patterns.
    """

    def score_velocity(
        self,
        metrics: VelocityMetrics,
        velocity_threshold_seconds: float = 300.0,
    ) -> Tuple[float, str, List[str], Dict[str, float]]:
        """
        Evaluate velocity metrics and compute Velocity Alert Score (0-100),
        severity classification, reason codes, and component score breakdown.
        """
        if metrics.transfer_count <= 1:
            return 0.0, "LOW", [], {
                "transfer_frequency": 0.0,
                "minimum_delta_t": 0.0,
                "average_delta_t": 0.0,
                "amount_volume": 0.0,
                "recipient_dispersion": 0.0,
                "downstream_continuity": 0.0,
            }

        score_components: Dict[str, float] = {}
        reason_codes: List[str] = []

        # 1. Transfer Frequency Factor (25 pts max)
        freq_score = min(25.0, metrics.transfer_count * 3.5)
        score_components["transfer_frequency"] = round(freq_score, 2)
        if metrics.transfer_count >= 5:
            reason_codes.append("HIGH_TRANSFER_FREQUENCY")

        # 2. Minimum Delta T Factor (25 pts max)
        # Shortest gap < 30s = 25 pts, < 120s = 18 pts, < 300s = 12 pts, < 600s = 5 pts
        if metrics.minimum_delta_t is None:
            min_delta_score = 0.0
        elif metrics.minimum_delta_t <= 30.0:
            min_delta_score = 25.0
        elif metrics.minimum_delta_t <= 120.0:
            min_delta_score = 18.0
        elif metrics.minimum_delta_t <= 300.0:
            min_delta_score = 12.0
        elif metrics.minimum_delta_t <= 600.0:
            min_delta_score = 5.0
        else:
            min_delta_score = 0.0

        score_components["minimum_delta_t"] = min_delta_score
        if min_delta_score >= 12.0:
            reason_codes.append("RAPID_SUCCESSIVE_TRANSFERS")

        # 3. Average Delta T Factor (20 pts max)
        if metrics.average_delta_t is None:
            avg_delta_score = 0.0
        elif metrics.average_delta_t <= 60.0:
            avg_delta_score = 20.0
        elif metrics.average_delta_t <= 300.0:
            avg_delta_score = 15.0
        elif metrics.average_delta_t <= 900.0:
            avg_delta_score = 10.0
        elif metrics.average_delta_t <= 3600.0:
            avg_delta_score = 5.0
        else:
            avg_delta_score = 0.0

        score_components["average_delta_t"] = avg_delta_score

        # 4. Amount Volume Factor (15 pts max)
        if metrics.total_amount >= 100000.0:
            amt_score = 15.0
        elif metrics.total_amount >= 25000.0:
            amt_score = 11.0
        elif metrics.total_amount >= 5000.0:
            amt_score = 7.0
        elif metrics.total_amount >= 1000.0:
            amt_score = 4.0
        else:
            amt_score = 1.0

        score_components["amount_volume"] = amt_score
        if amt_score >= 11.0 and (min_delta_score >= 12.0 or avg_delta_score >= 15.0):
            reason_codes.append("HIGH_VALUE_RAPID_MOVEMENT")

        # 5. Unique Recipient Dispersion (10 pts max)
        dispersion_score = min(10.0, metrics.unique_recipients * 2.0)
        score_components["recipient_dispersion"] = round(dispersion_score, 2)

        # 6. Downstream Hop Continuity (5 pts max)
        hop_score = min(5.0, metrics.downstream_hops * 1.5)
        score_components["downstream_continuity"] = round(hop_score, 2)
        if metrics.downstream_hops >= 2 and avg_delta_score >= 10.0:
            reason_codes.append("RAPID_DOWNSTREAM_MOVEMENT")
            reason_codes.append("MULTI_HOP_RAPID_FLOW")

        # Deduplicate reason codes
        reason_codes = list(dict.fromkeys(reason_codes))

        # Total raw score (0 - 100)
        raw_score = sum(score_components.values())
        velocity_score = round(min(100.0, max(0.0, raw_score)), 2)

        # Classify Severity
        if velocity_score >= 80.0:
            severity = "CRITICAL"
        elif velocity_score >= 60.0:
            severity = "HIGH"
        elif velocity_score >= 40.0:
            severity = "MODERATE"
        else:
            severity = "LOW"

        return velocity_score, severity, reason_codes, score_components
