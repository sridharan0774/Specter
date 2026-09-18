import logging
from typing import List, Dict, Any, Tuple
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse, TypologyResult

logger = logging.getLogger("specter.risk.scorer")


class RiskScorer:
    """
    Calculates the Transaction-Flow Risk Indicator (0-100) combining:
    - High-velocity movement intensity
    - Structural typology pattern contributions
    - Multihop flow complexity and value retention
    - Known Service Entity false positive mitigations
    """

    def calculate_risk_score(
        self,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
    ) -> Tuple[float, float, float, str, str, Dict[str, float], List[str], bool, bool, List[str]]:
        """
        Calculates transparent risk score (0-100), raw risk score, contextual risk score,
        contextual interpretation, risk level (LOW, MODERATE, HIGH, CRITICAL),
        component score breakdown, contributing factors, service entity context, and false positive mitigations.
        """
        component_contributions: Dict[str, float] = {
            "velocity_contribution": 0.0,
            "typology_contribution": 0.0,
            "flow_complexity_contribution": 0.0,
        }
        contributing_factors: List[str] = []
        false_positive_mitigations: List[str] = []

        # 1. Velocity Contribution (0 - 30 pts)
        v_score = 0.0
        if velocity_resp.alerts:
            top_v_alert = max(velocity_resp.alerts, key=lambda a: a.velocity_score)
            v_score = min(30.0, (top_v_alert.velocity_score / 100.0) * 30.0)
            contributing_factors.append(
                f"High-velocity movement detected (Score: {top_v_alert.velocity_score:.1f}/100)"
            )
            contributing_factors.extend(top_v_alert.reason_codes)

        component_contributions["velocity_contribution"] = round(v_score, 2)

        # 2. Typology Pattern Contribution (0 - 40 pts)
        typ_score = 0.0
        is_known_service_entity = False

        for t in typology_resp.typologies:
            if t.is_known_service or t.typology_name == "KNOWN_SERVICE_ENTITY":
                is_known_service_entity = True
                continue

            # Weight active typologies
            if t.severity == "CRITICAL":
                w = 20.0
            elif t.severity == "HIGH":
                w = 15.0
            elif t.severity == "MODERATE":
                w = 10.0
            else:
                w = 5.0

            typ_score += w * min(1.0, max(0.1, t.confidence))
            contributing_factors.append(f"Typology pattern detected: {t.typology_name} ({t.severity})")

        typ_score = min(40.0, typ_score)
        component_contributions["typology_contribution"] = round(typ_score, 2)

        # 3. Flow Complexity & Downstream Retention Contribution (0 - 30 pts)
        complexity_score = 0.0
        downstream_hops = velocity_resp.metrics.get("downstream_hops", 0)
        recipients = velocity_resp.metrics.get("unique_recipients", 0)

        if downstream_hops >= 3:
            complexity_score += 15.0
            contributing_factors.append(f"Deep multi-hop trace structure ({downstream_hops} hops)")
        elif downstream_hops >= 2:
            complexity_score += 10.0

        if recipients >= 5:
            complexity_score += 15.0
            contributing_factors.append(f"High recipient dispersion ({recipients} recipients)")
        elif recipients >= 3:
            complexity_score += 8.0

        complexity_score = min(30.0, complexity_score)
        component_contributions["flow_complexity_contribution"] = round(complexity_score, 2)

        # Raw combined risk score (0 - 100)
        raw_risk_score = round(min(100.0, max(0.0, sum(component_contributions.values()))), 2)
        service_entity_context = is_known_service_entity

        if service_entity_context:
            contextual_risk_score = round(min(35.0, raw_risk_score * 0.50), 2)
            contextual_interpretation = "NON_CRIMINAL_SERVICE_ENTITY_MITIGATION"
            false_positive_mitigations.append(
                f"Mitigation Applied (KNOWN_SERVICE_ENTITY): Target/Endpoint identified as known VASP/Exchange service. "
                f"SERVICE_ENTITY_CONTEXT = True. Raw transaction-flow risk indicator ({raw_risk_score:.1f}/100) retained for structural evidence; "
                f"contextual risk score adjusted to {contextual_risk_score:.1f}/100 as non-criminal service entity mitigation."
            )
        else:
            contextual_risk_score = raw_risk_score
            contextual_interpretation = "STANDARD_TRANSACTION_FLOW"

        final_risk_score = contextual_risk_score

        # Determine Risk Level
        if final_risk_score >= 85.0:
            risk_level = "CRITICAL"
        elif final_risk_score >= 65.0:
            risk_level = "HIGH"
        elif final_risk_score >= 40.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        # Deduplicate contributing factors
        contributing_factors = list(dict.fromkeys(contributing_factors))
        false_positive_mitigations = list(dict.fromkeys(false_positive_mitigations))

        return (
            final_risk_score,
            raw_risk_score,
            contextual_risk_score,
            contextual_interpretation,
            risk_level,
            component_contributions,
            contributing_factors,
            is_known_service_entity,
            service_entity_context,
            false_positive_mitigations,
        )
