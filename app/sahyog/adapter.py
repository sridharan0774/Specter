import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.schemas.investigation import (
    InvestigationSummarySchema,
    FindingSchema,
    EvidenceGraphItemSchema,
)
from app.schemas.trace import TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse

logger = logging.getLogger("specter.sahyog.adapter")


class SahyogAdapter:
    """
    Export Adapter producing structured SAHYOG-ready intelligence packages.
    
    IMPORTANT: This adapter ONLY builds structured export packages for official
    law enforcement / portal upload. It NEVER executes automatic external SAHYOG submission.
    
    Package Header:
    SAHYOG INTEGRATION STATUS: READY FOR AUTHORISED API INTEGRATION
    """

    INTEGRATION_STATUS = "READY FOR AUTHORISED API INTEGRATION"

    def build_sahyog_package(
        self,
        summary: InvestigationSummarySchema,
        findings: List[FindingSchema],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        risk_resp: RiskIndicatorResponse,
        vasp_resp: VASPAttributionResponse,
    ) -> Dict[str, Any]:
        """Generates a complete, structured SAHYOG-compliant JSON export payload."""
        now_str = datetime.now(timezone.utc).isoformat()

        # Format paths for SAHYOG schema
        sahyog_paths = []
        for p in trace_result.paths:
            sahyog_paths.append({
                "path_id": p.path_id,
                "hop_count": p.hop_count,
                "wallet_sequence": p.wallet_sequence,
                "initial_amount_usdt": p.initial_amount,
                "final_amount_usdt": p.final_amount,
                "value_retention_percent": p.value_retention_percent,
                "elapsed_time_seconds": p.elapsed_time_seconds,
                "relevance_score": p.relevance_score,
                "transactions": [
                    {
                        "hop_number": hop.hop_number,
                        "from_wallet": hop.from_address,
                        "to_wallet": hop.to_address,
                        "tx_hash": hop.tx_hash,
                        "amount_usdt": hop.amount,
                        "timestamp": hop.timestamp,
                        "delta_t_seconds": hop.delta_t_seconds,
                        "explorer_url": hop.explorer_url,
                    }
                    for hop in p.hops
                ],
            })

        # Format VASP attribution for SAHYOG
        vasp_info = {}
        if vasp_resp and vasp_resp.candidates:
            top_vasp = vasp_resp.candidates[0]
            vasp_info = {
                "attributed_vasp_name": top_vasp.candidate_name,
                "attribution_type": top_vasp.attribution_type,
                "confidence_score": top_vasp.attribution_confidence,
                "matched_wallet": top_vasp.endpoint_address,
                "confidence_band": top_vasp.confidence_band,
                "all_candidates": [
                    {
                        "vasp_name": c.candidate_name,
                        "attribution_score": c.attribution_confidence,
                        "matched_address": c.endpoint_address,
                        "attribution_type": c.attribution_type,
                    }
                    for c in vasp_resp.candidates
                ],
            }

        # Format findings for SAHYOG
        sahyog_findings = [f.model_dump(mode="json") for f in findings]

        # Format evidence graph items for SAHYOG
        sahyog_evidence = [e.model_dump(mode="json") for e in evidence_items]

        # Format velocity alerts
        sahyog_alerts = [a.model_dump(mode="json") for a in velocity_resp.alerts]

        package = {
            "sahyog_metadata": {
                "integration_status": self.INTEGRATION_STATUS,
                "generator_engine": "Specter High-Velocity Blockchain Intelligence Platform v1.0",
                "export_timestamp": now_str,
                "schema_version": "SAHYOG_READY_V1",
                "notice": "CONFIDENTIAL LAW ENFORCEMENT INVESTIGATION PACKAGE - AUTHORISED USE ONLY",
            },
            "case_details": {
                "case_id": summary.case_id,
                "job_id": summary.job_id,
                "target_wallet": summary.target_wallet,
                "chain": summary.chain,
                "asset": summary.asset,
                "investigation_status": summary.investigation_status,
                "execution_duration_seconds": summary.execution_duration_seconds,
                "completed_at": summary.completed_at.isoformat() if hasattr(summary.completed_at, "isoformat") else str(summary.completed_at),
            },
            "risk_assessment": {
                "risk_score": risk_resp.risk_score,
                "raw_risk_score": risk_resp.raw_risk_score,
                "contextual_risk_score": risk_resp.contextual_risk_score,
                "risk_level": risk_resp.risk_level,
                "service_entity_context": risk_resp.service_entity_context,
                "contextual_interpretation": risk_resp.contextual_interpretation,
                "is_known_service_entity": risk_resp.is_known_service_entity,
                "component_contributions": risk_resp.component_contributions,
                "contributing_factors": risk_resp.contributing_factors,
                "false_positive_mitigations": risk_resp.false_positive_mitigations,
            },
            "vasp_attribution": vasp_info,
            "analytical_findings": sahyog_findings,
            "evidence_ledger": sahyog_evidence,
            "velocity_analysis": {
                "has_high_velocity": velocity_resp.has_high_velocity_pattern,
                "alerts_count": len(velocity_resp.alerts),
                "summary": velocity_resp.summary,
                "metrics": velocity_resp.metrics,
                "alerts": sahyog_alerts,
            },
            "typology_analysis": {
                "typologies_count": len(typology_resp.typologies),
                "summary": typology_resp.summary,
                "typologies": [t.model_dump(mode="json") for t in typology_resp.typologies],
            },
            "fund_tracing_graph": {
                "total_wallets_traced": trace_result.total_wallets_discovered,
                "total_transactions_analyzed": trace_result.total_transactions_analyzed,
                "total_paths_found": trace_result.total_paths_found,
                "trace_paths": sahyog_paths,
            },
        }

        return package
