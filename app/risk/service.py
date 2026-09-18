import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.trace import TraceRun
from app.schemas.trace import TraceResultResponse
from app.schemas.risk import RiskIndicatorResponse
from app.velocity.service import VelocityService
from app.typologies.service import TypologyService
from app.risk.scorer import RiskScorer

logger = logging.getLogger("specter.risk.service")


class RiskService:
    """
    Service orchestrating the Transaction-Flow Risk Indicator computation
    combining velocity metrics, typologies, multi-hop retention, and false positive safety rules.
    """

    def __init__(self, db: Session):
        self.db = db
        self.velocity_service = VelocityService(db)
        self.typology_service = TypologyService(db)
        self.risk_scorer = RiskScorer()

    def analyze_trace(
        self,
        trace_result: TraceResultResponse,
        case_id: Optional[str] = None,
    ) -> RiskIndicatorResponse:
        """Compute Transaction-Flow Risk Indicator for a TraceResultResponse."""
        eff_case_id = case_id or trace_result.case_id

        # 1. Run velocity analysis
        velocity_resp = self.velocity_service.analyze_trace(trace_result, case_id=eff_case_id)

        # 2. Run typology analysis
        typology_resp = self.typology_service.analyze_trace(trace_result, case_id=eff_case_id)

        # 3. Calculate Risk Score
        (
            risk_score,
            raw_risk_score,
            contextual_risk_score,
            contextual_interpretation,
            risk_level,
            component_contributions,
            contributing_factors,
            is_known_service_entity,
            service_entity_context,
            false_positive_mitigations,
        ) = self.risk_scorer.calculate_risk_score(velocity_resp, typology_resp)

        return RiskIndicatorResponse(
            trace_id=trace_result.trace_id,
            case_id=eff_case_id,
            starting_wallet=trace_result.starting_wallet,
            chain=trace_result.chain,
            asset=trace_result.asset,
            risk_score=risk_score,
            raw_risk_score=raw_risk_score,
            contextual_risk_score=contextual_risk_score,
            contextual_interpretation=contextual_interpretation,
            risk_level=risk_level,
            component_contributions=component_contributions,
            contributing_factors=contributing_factors,
            is_known_service_entity=is_known_service_entity,
            service_entity_context=service_entity_context,
            false_positive_mitigations=false_positive_mitigations,
            analyzed_at=datetime.now(timezone.utc),
        )

    def analyze_trace_id(
        self,
        trace_id: str,
        case_id: Optional[str] = None,
    ) -> RiskIndicatorResponse:
        """Fetch trace run from DB and compute Transaction-Flow Risk Indicator."""
        trace_run = self.db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
        if not trace_run:
            raise ValueError(f"Trace run '{trace_id}' not found.")

        trace_result = self.velocity_service._reconstruct_trace_result(trace_run)
        return self.analyze_trace(
            trace_result=trace_result,
            case_id=case_id or trace_run.case_id,
        )
