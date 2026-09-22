import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceItem
from app.models.finding import Finding
from app.schemas.investigation import FindingSchema, EvidenceGraphItemSchema
from app.schemas.trace import TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse
from app.sources.registry import source_registry

logger = logging.getLogger("specter.evidence.builder")


class EvidenceBuilder:
    """
    Builds structured, traceable Evidence Ledger items and analytical Findings
    establishing the formal evidence graph:
    Finding -> Evidence Item -> Transaction / Wallet / Path -> Source Metadata -> Explorer URL.
    """

    def __init__(self, db: Session):
        self.db = db

    def build_evidence_graph_and_findings(
        self,
        case_id: str,
        job_id: str,
        trace_result: TraceResultResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        risk_resp: RiskIndicatorResponse,
        vasp_resp: Optional[VASPAttributionResponse] = None,
    ) -> Tuple[List[FindingSchema], List[EvidenceGraphItemSchema]]:
        """
        Synthesizes all analytical components into formal findings and traceable evidence items,
        persisting them into the database.
        """
        findings: List[FindingSchema] = []
        evidence_items: List[EvidenceGraphItemSchema] = []

        # 1. Risk Indicator Finding & Evidence
        risk_fnd_id = f"fnd-risk-{uuid.uuid4().hex[:8]}"
        risk_ev_id = f"ev-risk-{uuid.uuid4().hex[:8]}"

        risk_src = source_registry.get_source("SRC_SPECTER_RISK_ENGINE")
        risk_ev = EvidenceGraphItemSchema(
            evidence_id=risk_ev_id,
            finding_id=risk_fnd_id,
            case_id=case_id,
            evidence_type="RISK_INDICATOR_ASSESSMENT",
            finding=f"Transaction-Flow Risk Indicator assessed at {risk_resp.risk_score:.1f}/100 ({risk_resp.risk_level} risk level). Raw structural score: {risk_resp.raw_risk_score:.1f}/100.",
            supporting_tx_hashes=[],
            supporting_addresses=[trace_result.starting_wallet],
            supporting_path_ids=[p.path_id for p in trace_result.paths],
            source_id=risk_src.source_id if risk_src else "SRC_SPECTER_RISK_ENGINE",
            source_name=risk_src.name if risk_src else "Specter Risk Intelligence Engine v1.0",
            explorer_urls=[],
            confidence=0.90,
            scoring_factors={
                "risk_score": risk_resp.risk_score,
                "raw_risk_score": risk_resp.raw_risk_score,
                "contextual_risk_score": risk_resp.contextual_risk_score,
                "service_entity_context": risk_resp.service_entity_context,
                "contextual_interpretation": risk_resp.contextual_interpretation,
                "component_contributions": risk_resp.component_contributions,
            },
        )
        evidence_items.append(risk_ev)

        risk_fnd = FindingSchema(
            finding_id=risk_fnd_id,
            case_id=case_id,
            job_id=job_id,
            finding_type="TRANSACTION_FLOW_RISK",
            title=f"Transaction-Flow Risk Indicator: {risk_resp.risk_level} ({risk_resp.risk_score:.1f}/100)",
            description=(
                f"Composite risk indicator for target wallet {trace_result.starting_wallet}. "
                f"Raw structural risk score: {risk_resp.raw_risk_score:.1f}/100. "
                f"Service Entity Context: {risk_resp.service_entity_context}. "
                f"Interpretation: {risk_resp.contextual_interpretation}. "
                f"Contributing factors: {', '.join(risk_resp.contributing_factors) if risk_resp.contributing_factors else 'None'}."
            ),
            severity="CRITICAL" if risk_resp.risk_level == "CRITICAL" else ("HIGH" if risk_resp.risk_level == "HIGH" else "MODERATE"),
            confidence=0.90,
            supporting_evidence_ids=[risk_ev_id],
            metadata={
                "risk_score": risk_resp.risk_score,
                "raw_risk_score": risk_resp.raw_risk_score,
                "contextual_risk_score": risk_resp.contextual_risk_score,
                "service_entity_context": risk_resp.service_entity_context,
                "mitigations": risk_resp.false_positive_mitigations,
            },
        )
        findings.append(risk_fnd)

        # 2. Velocity Movement Alerts Findings & Evidence
        vel_src = source_registry.get_source("SRC_SPECTER_VELOCITY_ENGINE")
        chain_name = trace_result.chain if trace_result else "TRON"
        from app.blockchain.registry import ChainRegistry
        adapter = ChainRegistry.get_adapter(chain_name)

        if velocity_resp.alerts:
            for alert in velocity_resp.alerts:
                ev_id = f"ev-vel-{uuid.uuid4().hex[:8]}"
                fnd_id = f"fnd-vel-{uuid.uuid4().hex[:8]}"

                ev_item = EvidenceGraphItemSchema(
                    evidence_id=ev_id,
                    finding_id=fnd_id,
                    case_id=case_id,
                    evidence_type="VELOCITY_ALERT",
                    finding=f"High-velocity movement alert: {alert.explanation}",
                    supporting_tx_hashes=alert.supporting_transactions,
                    supporting_addresses=alert.supporting_wallets,
                    supporting_path_ids=[],
                    source_id=vel_src.source_id if vel_src else "SRC_SPECTER_VELOCITY_ENGINE",
                    source_name=vel_src.name if vel_src else "Specter High-Velocity Movement Engine v1.0",
                    explorer_urls=[
                        adapter.get_explorer_url(h) for h in alert.supporting_transactions
                    ],
                    confidence=0.92,
                    scoring_factors={
                        "velocity_score": alert.velocity_score,
                        "minimum_delta_t": alert.minimum_delta_t,
                        "average_delta_t": alert.average_delta_t,
                        "transfer_count": alert.transfer_count,
                        "total_amount": alert.total_amount,
                    },
                )
                evidence_items.append(ev_item)

                fnd = FindingSchema(
                    finding_id=fnd_id,
                    case_id=case_id,
                    job_id=job_id,
                    finding_type="HIGH_VELOCITY_MOVEMENT",
                    title=f"Rapid Successive Fund Movement ({alert.severity} Severity)",
                    description=alert.explanation,
                    severity=alert.severity,
                    confidence=0.92,
                    supporting_evidence_ids=[ev_id],
                    metadata={
                        "velocity_score": alert.velocity_score,
                        "transfer_count": alert.transfer_count,
                        "total_amount": alert.total_amount,
                        "reason_codes": alert.reason_codes,
                    },
                )
                findings.append(fnd)

        # 3. Transaction Typology Pattern Findings & Evidence
        typ_src = source_registry.get_source("SRC_SPECTER_TYPOLOGY_ENGINE")
        for typ in typology_resp.typologies:
            ev_id = f"ev-typ-{uuid.uuid4().hex[:8]}"
            fnd_id = f"fnd-typ-{uuid.uuid4().hex[:8]}"

            ev_item = EvidenceGraphItemSchema(
                evidence_id=ev_id,
                finding_id=fnd_id,
                case_id=case_id,
                evidence_type="TYPOLOGY_PATTERN",
                finding=f"Detected structural transaction typology: {typ.typology_name}. {typ.description}",
                supporting_tx_hashes=typ.supporting_transactions,
                supporting_addresses=typ.supporting_wallets,
                supporting_path_ids=[],
                source_id=typ_src.source_id if typ_src else "SRC_SPECTER_TYPOLOGY_ENGINE",
                source_name=typ_src.name if typ_src else "Specter Transaction Typology Engine v1.0",
                explorer_urls=[
                    adapter.get_explorer_url(h) for h in typ.supporting_transactions
                ],
                confidence=typ.confidence,
                scoring_factors=typ.metrics,
            )
            evidence_items.append(ev_item)

            fnd = FindingSchema(
                finding_id=fnd_id,
                case_id=case_id,
                job_id=job_id,
                finding_type=typ.typology_name,
                title=f"Transaction Typology Pattern: {typ.typology_name.replace('_', ' ').title()}",
                description=typ.description,
                severity=typ.severity,
                confidence=typ.confidence,
                supporting_evidence_ids=[ev_id],
                metadata={
                    "is_known_service": typ.is_known_service,
                    "metrics": typ.metrics,
                },
            )
            findings.append(fnd)

        # 4. VASP Attribution Findings & Evidence
        if vasp_resp:
            vasp_src = source_registry.get_source("SRC_SPECTER_VASP_DB")
            ev_id = f"ev-vasp-{uuid.uuid4().hex[:8]}"
            fnd_id = f"fnd-vasp-{uuid.uuid4().hex[:8]}"

            if vasp_resp.status == "RESOLVED" and vasp_resp.candidates:
                top_candidate = vasp_resp.candidates[0]

                ev_item = EvidenceGraphItemSchema(
                    evidence_id=ev_id,
                    finding_id=fnd_id,
                    case_id=case_id,
                    evidence_type="VASP_RESOLUTION",
                    finding=f"Likely VASP Attribution candidate resolved: {top_candidate.candidate_name} ({top_candidate.attribution_type}) with score {top_candidate.attribution_confidence:.1f}/100",
                    supporting_tx_hashes=[h for p in trace_result.paths for h in [hop.tx_hash for hop in p.hops]],
                    supporting_addresses=[top_candidate.endpoint_address],
                    supporting_path_ids=[p.path_id for p in trace_result.paths],
                    source_id=vasp_src.source_id if vasp_src else "SRC_SPECTER_VASP_DB",
                    source_name=vasp_src.name if vasp_src else "Specter VASP Intelligence Database",
                    explorer_urls=[adapter.get_address_explorer_url(top_candidate.endpoint_address)],

                    confidence=top_candidate.source_confidence,
                    scoring_factors={
                        "attribution_score": top_candidate.attribution_confidence,
                        "matched_address": top_candidate.endpoint_address,
                        "confidence_band": top_candidate.confidence_band,
                        "hop_distance": top_candidate.endpoint_hop_distance,
                        "entity_role": top_candidate.entity_role,
                        "match_position": top_candidate.match_position,
                    },
                )
                evidence_items.append(ev_item)

                fnd = FindingSchema(
                    finding_id=fnd_id,
                    case_id=case_id,
                    job_id=job_id,
                    finding_type="VASP_ATTRIBUTION",
                    title=f"Likely VASP Attribution: {top_candidate.candidate_name}",
                    description=(
                        f"Evidence-backed fund flow analysis indicates likely VASP attribution to '{top_candidate.candidate_name}' "
                        f"({top_candidate.entity_role}, {top_candidate.attribution_type}). Matched endpoint address: {top_candidate.endpoint_address} "
                        f"at {top_candidate.endpoint_hop_distance}-hop distance with {top_candidate.confidence_band} confidence "
                        f"(Score: {top_candidate.attribution_confidence:.1f}/100). Does not constitute legal proof of beneficial ownership."
                    ),
                    severity="INFO",
                    confidence=top_candidate.source_confidence,
                    supporting_evidence_ids=[ev_id],
                    metadata={
                        "vasp_name": top_candidate.candidate_name,
                        "entity_role": top_candidate.entity_role,
                        "attribution_type": top_candidate.attribution_type,
                        "matched_address": top_candidate.endpoint_address,
                        "hop_distance": top_candidate.endpoint_hop_distance,
                        "why_this_vasp": top_candidate.why_this_vasp,
                    },
                )
                findings.append(fnd)
            else:
                # Useful negative result finding
                ev_item = EvidenceGraphItemSchema(
                    evidence_id=ev_id,
                    finding_id=fnd_id,
                    case_id=case_id,
                    evidence_type="VASP_RESOLUTION",
                    finding="No high-confidence VASP identified across traced fund flow endpoints.",
                    supporting_tx_hashes=[h for p in trace_result.paths for h in [hop.tx_hash for hop in p.hops]],
                    supporting_addresses=[p.wallet_sequence[-1] for p in trace_result.paths if p.wallet_sequence],
                    supporting_path_ids=[p.path_id for p in trace_result.paths],
                    source_id=vasp_src.source_id if vasp_src else "SRC_SPECTER_VASP_DB",
                    source_name=vasp_src.name if vasp_src else "Specter VASP Intelligence Database",
                    confidence=1.0,
                    scoring_factors={"status": vasp_resp.status},
                )
                evidence_items.append(ev_item)

                fnd = FindingSchema(
                    finding_id=fnd_id,
                    case_id=case_id,
                    job_id=job_id,
                    finding_type="VASP_ATTRIBUTION",
                    title="VASP Attribution: No High-Confidence VASP Identified",
                    description=(
                        "The traced fund flow did not provide sufficient evidence to associate the endpoint with a known VASP. "
                        f"{vasp_resp.negative_reason or ''} This is a valid investigation result."
                    ),
                    severity="INFO",
                    confidence=1.0,
                    supporting_evidence_ids=[ev_id],
                    metadata={
                        "status": vasp_resp.status,
                        "candidates_considered_count": vasp_resp.candidates_considered_count,
                        "negative_reason": vasp_resp.negative_reason,
                    },
                )
                findings.append(fnd)

        # 5. Save to SQLite Database
        self._persist_to_db(case_id, findings, evidence_items)

        return findings, evidence_items

    def _persist_to_db(
        self,
        case_id: str,
        findings: List[FindingSchema],
        evidence_items: List[EvidenceGraphItemSchema],
    ):
        """Save findings and evidence items to SQL DB."""
        for f in findings:
            db_fnd = Finding(
                finding_id=f.finding_id,
                case_id=case_id,
                job_id=f.job_id,
                finding_type=f.finding_type,
                title=f.title,
                description=f.description,
                severity=f.severity,
                confidence=f.confidence,
                supporting_evidence_ids=f.supporting_evidence_ids,
                metadata_json=f.metadata,
            )
            self.db.add(db_fnd)

        for ev in evidence_items:
            db_ev = EvidenceItem(
                case_id=case_id,
                finding=ev.finding,
                supporting_tx_hashes=ev.supporting_tx_hashes,
                supporting_addresses=ev.supporting_addresses,
                source=ev.source_name,
                retrieval_timestamp=ev.retrieval_timestamp,
                scoring_factors=ev.scoring_factors,
                confidence=ev.confidence,
                explorer_urls=ev.explorer_urls,
            )
            self.db.add(db_ev)

        self.db.commit()
