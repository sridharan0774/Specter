import logging
from typing import List, Dict, Any
from app.schemas.typology import TypologyResult

logger = logging.getLogger("specter.typologies.evidence")


class TypologyEvidenceBuilder:
    """
    Constructs explainable evidence summaries and analytical explanations
    for detected transaction typologies.
    """

    def generate_summary(
        self,
        typologies: List[TypologyResult],
        starting_wallet: str,
    ) -> str:
        """Generate human-readable analytical summary of detected typologies."""
        if not typologies:
            return f"NO HIGH-RISK STRUCTURAL PATTERNS DETECTED for starting wallet {starting_wallet}."

        is_known_service = any(t.is_known_service for t in typologies)
        typ_names = [t.typology_name for t in typologies if t.typology_name != "KNOWN_SERVICE_ENTITY"]

        if not typ_names and is_known_service:
            return f"KNOWN SERVICE ENTITY IDENTIFIED: Target or starting wallet is a recognized exchange/custodian endpoint. No suspicious layering structure observed."

        service_note = " (Note: Identified as KNOWN SERVICE ENTITY)" if is_known_service else ""
        pattern_str = ", ".join(typ_names) if typ_names else "GENERAL_FLOW"

        return (
            f"STRUCTURAL PATTERNS IDENTIFIED{service_note}: Detected {len(typ_names)} structural typology pattern(s) "
            f"[{pattern_str}] across trace graph starting at {starting_wallet[:10]}..."
        )

    def build_evidence_ledger(self, typologies: List[TypologyResult]) -> List[Dict[str, Any]]:
        """Build machine-readable evidence ledger for case management and reporting."""
        ledger = []
        for t in typologies:
            ledger.append(
                {
                    "typology_id": t.typology_id,
                    "typology_name": t.typology_name,
                    "severity": t.severity,
                    "description": t.description,
                    "confidence": t.confidence,
                    "is_known_service": t.is_known_service,
                    "metrics": t.metrics,
                    "trigger_conditions": t.trigger_conditions,
                    "supporting_transactions": t.supporting_transactions,
                    "supporting_wallets": t.supporting_wallets,
                    "supporting_paths": t.supporting_paths,
                }
            )
        return ledger
