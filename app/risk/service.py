import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.trace import TraceRun
from app.models.risk import RiskAssessmentRecord
from app.schemas.trace import TraceResultResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse
from app.velocity.service import VelocityService
from app.typologies.service import TypologyService
from app.intelligence.risk_engine import ExplainableGraphRiskEngine

logger = logging.getLogger("specter.risk.service")


class RiskService:
    """
    Service orchestrating the Explainable Graph Risk Engine (EGRE_V1) computation
    combining velocity metrics, typologies, multi-hop retention, VASP context,
    and dimension-level correlation control.
    """

    def __init__(self, db: Session):
        self.db = db
        self.velocity_service = VelocityService(db)
        self.typology_service = TypologyService(db)
        self.egre_engine = ExplainableGraphRiskEngine()

    def analyze_trace(
        self,
        trace_result: TraceResultResponse,
        case_id: Optional[str] = None,
        vasp_resp: Optional[VASPAttributionResponse] = None,
    ) -> RiskIndicatorResponse:
        """Compute Explainable Graph Risk Indicator for a TraceResultResponse."""
        eff_case_id = case_id or trace_result.case_id

        # 1. Run velocity analysis
        velocity_resp = self.velocity_service.analyze_trace(trace_result, case_id=eff_case_id)

        # 2. Run typology analysis
        typology_resp = self.typology_service.analyze_trace(trace_result, case_id=eff_case_id)

        # 3. Execute EGRE_V1 Risk Calculation
        risk_resp = self.egre_engine.evaluate_risk(
            trace_result=trace_result,
            velocity_resp=velocity_resp,
            typology_resp=typology_resp,
            vasp_resp=vasp_resp,
            case_id=eff_case_id,
        )

        # 4. Optionally persist to database if case_id is present
        if eff_case_id and self.db:
            try:
                rec = RiskAssessmentRecord(
                    case_id=eff_case_id,
                    starting_wallet=risk_resp.starting_wallet,
                    chain=risk_resp.chain,
                    asset=risk_resp.asset,
                    risk_score=risk_resp.risk_score,
                    raw_risk_score=risk_resp.raw_risk_score,
                    contextual_risk_score=risk_resp.contextual_risk_score,
                    risk_level=risk_resp.risk_level,
                    assessment_status=risk_resp.assessment_status,
                    calculation_version=risk_resp.calculation_version,
                    dimension_scores=risk_resp.dimension_scores,
                    indicators=[ind.model_dump(mode="json") for ind in risk_resp.indicators],
                    component_contributions=risk_resp.component_contributions,
                    contributing_factors=risk_resp.contributing_factors,
                    false_positive_mitigations=risk_resp.false_positive_mitigations,
                )
                self.db.add(rec)
                self.db.commit()
            except Exception as e:
                logger.warning(f"Notice: RiskAssessmentRecord persistence: {e}")

        return risk_resp

    def analyze_trace_id(
        self,
        trace_id: str,
        case_id: Optional[str] = None,
        vasp_resp: Optional[VASPAttributionResponse] = None,
    ) -> RiskIndicatorResponse:
        """Fetch trace run from DB and compute Risk Indicator."""
        trace_run = self.db.query(TraceRun).filter(TraceRun.trace_id == trace_id).first()
        if not trace_run:
            raise ValueError(f"Trace run '{trace_id}' not found.")

        trace_result = self.velocity_service._reconstruct_trace_result(trace_run)
        return self.analyze_trace(
            trace_result=trace_result,
            case_id=case_id or trace_run.case_id,
            vasp_resp=vasp_resp,
        )

