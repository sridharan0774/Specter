import logging
from typing import List, Dict, Any, Tuple
from app.schemas.typology import TypologyResult

logger = logging.getLogger("specter.typologies.scorer")


class TypologyScorer:
    """
    Evaluates detected typologies and computes composite severity,
    pattern weights, and context indicators.
    """

    TYPOLOGY_WEIGHTS = {
        "FAN_OUT": 25.0,
        "FAN_IN": 25.0,
        "CONSOLIDATION": 30.0,
        "RAPID_PEEL_LIKE_MOVEMENT": 35.0,
        "REPEATED_INTERACTION": 15.0,
        "VASP_CONVERGENCE": 20.0,
        "KNOWN_SERVICE_ENTITY": 0.0,  # Safety mitigation, 0 risk weight
    }

    SEVERITY_MULTIPLIERS = {
        "CRITICAL": 1.0,
        "HIGH": 0.85,
        "MODERATE": 0.60,
        "LOW": 0.30,
    }

    def score_typologies(self, typologies: List[TypologyResult]) -> Tuple[float, List[str]]:
        """
        Calculates raw composite typology score (0-100) and extracts active pattern list.
        """
        if not typologies:
            return 0.0, []

        active_patterns: List[str] = []
        raw_score = 0.0

        for t in typologies:
            if t.typology_name == "KNOWN_SERVICE_ENTITY":
                continue

            active_patterns.append(t.typology_name)
            base_w = self.TYPOLOGY_WEIGHTS.get(t.typology_name, 10.0)
            sev_mult = self.SEVERITY_MULTIPLIERS.get(t.severity, 0.50)
            conf = max(0.1, min(1.0, t.confidence))

            contribution = base_w * sev_mult * conf
            raw_score += contribution

        composite_score = round(min(100.0, max(0.0, raw_score)), 2)
        return composite_score, active_patterns
