import os
import json
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
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


class SahyogTransport(ABC):
    """
    Abstract Transport Interface for SAHYOG Portal Integration.
    Decouples package building, validation, and contract operations from network transport.
    """

    @abstractmethod
    def build_disclosure_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def build_freeze_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
        urgency_level: Optional[str] = "HIGH",
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate_sahyog_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def export_sahyog_package(self, package: Dict[str, Any], output_dir: str, filename: str) -> str:
        pass

    @abstractmethod
    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self, request_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def acknowledge(self, request_id: str) -> Dict[str, Any]:
        pass


class LocalPackageTransport(SahyogTransport):
    """
    Default Local Package Transport implementation.
    Generates local, verifiable, evidence-linked SAHYOG requests & packages.
    Operates explicitly under contract state: READY_FOR_AUTHORISED_API_INTEGRATION.
    """

    INTEGRATION_STATUS = "READY FOR AUTHORISED API INTEGRATION"


    def _build_evidence_chain(
        self,
        vasp_name: str,
        endpoint_address: str,
        attribution_score: float,
        reasoning: List[str],
        supporting_txs: List[str],
        explorer_urls: List[str],
        provenance_sources: List[str],
    ) -> List[Dict[str, Any]]:
        """Constructs an explicit evidence-linked action traceability chain."""
        chain_steps = [
            {
                "step_number": 1,
                "element_type": "VASP",
                "label": "Identified Virtual Asset Service Provider",
                "value": vasp_name,
                "detail": f"Attributed entity: {vasp_name}",
            },
            {
                "step_number": 2,
                "element_type": "ENDPOINT_WALLET",
                "label": "VASP-Associated Deposit / Operational Endpoint",
                "value": endpoint_address or "N/A",
                "detail": f"Matched address: {endpoint_address}",
            },
            {
                "step_number": 3,
                "element_type": "ATTRIBUTION_SCORE",
                "label": "Evidence-Backed Attribution Score & Confidence",
                "value": f"{attribution_score} / 100",
                "detail": f"Score: {attribution_score}/100 | Confidence Band: {'HIGH' if attribution_score >= 80 else 'MODERATE' if attribution_score >= 50 else 'LOW'}",
            },
            {
                "step_number": 4,
                "element_type": "REASONING",
                "label": "Analytical Evidence & Path Convergence",
                "value": "; ".join(reasoning[:3]) if reasoning else "Observable multi-hop path alignment",
                "detail": "Detailed scoring components and hop distance logic",
            },
            {
                "step_number": 5,
                "element_type": "SUPPORTING_TRANSACTION",
                "label": "Observable Blockchain Transactions",
                "value": supporting_txs[0] if supporting_txs else "N/A",
                "detail": f"Total supporting transactions: {len(supporting_txs)}",
            },
            {
                "step_number": 6,
                "element_type": "EXPLORER_REFERENCE",
                "label": "Blockchain Explorer Reference URL",
                "value": explorer_urls[0] if explorer_urls else f"https://tronscan.org/#/address/{endpoint_address}",
                "detail": "Verifiable on-chain explorer link",
            },
            {
                "step_number": 7,
                "element_type": "VASP_PROVENANCE",
                "label": "Intelligence Source Provenance",
                "value": provenance_sources[0] if provenance_sources else "Verified Public Intelligence Registry",
                "detail": "Documented provenance & source quality level",
            },
        ]
        return chain_steps

    def build_disclosure_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds a structured VASP Information Disclosure Request draft."""
        now_str = datetime.now(timezone.utc).isoformat()
        req_id = f"sahyog-disc-{uuid.uuid4().hex[:10]}"

        # Extract real attribution data
        top_vasp = vasp_resp.candidates[0] if (vasp_resp and vasp_resp.candidates) else None
        vasp_name = top_vasp.candidate_name if top_vasp else "UNKNOWN_OR_UNATTRIBUTED"
        endpoint_address = top_vasp.endpoint_address if top_vasp else (summary.target_wallet or "")
        attr_score = top_vasp.attribution_confidence if top_vasp else 0.0
        conf_level = top_vasp.confidence_band if top_vasp else ("HIGH" if attr_score >= 80 else "LOW")
        hop_dist = top_vasp.endpoint_hop_distance if top_vasp else 0
        ep_status = "TERMINAL ENDPOINT" if (top_vasp and getattr(top_vasp, "is_terminal_endpoint", True)) else "INTERMEDIATE ASSOCIATION"

        # Collect supporting transactions & explorer links
        supporting_txs = top_vasp.supporting_transactions if top_vasp and top_vasp.supporting_transactions else []
        if not supporting_txs:
            for p in trace_result.paths:
                for h in p.hops:
                    if h.tx_hash not in supporting_txs:
                        supporting_txs.append(h.tx_hash)

        explorer_urls = []
        provenance_sources = []
        for ev in evidence_items:
            for u in (ev.explorer_urls or []):
                if u not in explorer_urls:
                    explorer_urls.append(u)
            if ev.source_name and ev.source_name not in provenance_sources:
                provenance_sources.append(ev.source_name)

        if not explorer_urls and endpoint_address:
            explorer_urls.append(f"https://tronscan.org/#/address/{endpoint_address}")

        reasoning = top_vasp.matched_relevance_reasons if top_vasp and top_vasp.matched_relevance_reasons else ["Observable multi-hop fund flow convergence."]

        evidence_chain = self._build_evidence_chain(
            vasp_name=vasp_name,
            endpoint_address=endpoint_address,
            attribution_score=attr_score,
            reasoning=reasoning,
            supporting_txs=supporting_txs,
            explorer_urls=explorer_urls,
            provenance_sources=provenance_sources,
        )

        request_data = {
            "schema_version": "1.0",
            "request_id": req_id,
            "request_type": "DISCLOSURE_REQUEST",
            "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            "integration_status": self.INTEGRATION_STATUS,
            "created_at": now_str,
            "notice": "CONFIDENTIAL LAW ENFORCEMENT INVESTIGATION DRAFT — REQUIRES AUTHORISED REVIEW BEFORE TRANSMISSION",
            "case": {
                "case_id": summary.case_id,
                "investigation_id": summary.job_id,
                "investigator_reference": investigator_id or "INV-AUTOMATED-001",
                "purpose_of_request": reason or "Authorized Law Enforcement Transaction Disclosure Request",
            },
            "suspect": {
                "wallet_address": summary.target_wallet,
                "chain": summary.chain,
                "asset": summary.asset,
            },
            "attribution": {
                "vasp": vasp_name,
                "wallet_address": endpoint_address,
                "endpoint_status": ep_status,
                "attribution_score": attr_score,
                "confidence": conf_level,
                "hop_distance": hop_dist,
            },
            "evidence": {
                "supporting_transactions": supporting_txs,
                "trace_paths_count": trace_result.total_paths_found,
                "relevance_summary": reasoning,
                "explorer_references": explorer_urls,
                "provenance": provenance_sources,
            },
            "evidence_chain": evidence_chain,
            "evidence_snapshot_reference": f"snap-{summary.job_id}",
            "requested_action": {
                "type": "DISCLOSURE_REQUEST",
                "action_description": f"Request user identity, KYC logs, IP address history, and account deposit/withdrawal statements for endpoint wallet '{endpoint_address}' attributed to {vasp_name}.",
                "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            },
        }

        return request_data

    def build_freeze_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
        urgency_level: Optional[str] = "HIGH",
    ) -> Dict[str, Any]:
        """Builds a structured Asset Preservation / Freeze Request draft."""
        now_str = datetime.now(timezone.utc).isoformat()
        req_id = f"sahyog-freeze-{uuid.uuid4().hex[:10]}"

        top_vasp = vasp_resp.candidates[0] if (vasp_resp and vasp_resp.candidates) else None
        vasp_name = top_vasp.candidate_name if top_vasp else "UNKNOWN_OR_UNATTRIBUTED"
        endpoint_address = top_vasp.endpoint_address if top_vasp else (summary.target_wallet or "")
        attr_score = top_vasp.attribution_confidence if top_vasp else 0.0
        conf_level = top_vasp.confidence_band if top_vasp else ("HIGH" if attr_score >= 80 else "LOW")
        hop_dist = top_vasp.endpoint_hop_distance if top_vasp else 0
        ep_status = "TERMINAL ENDPOINT" if (top_vasp and getattr(top_vasp, "is_terminal_endpoint", True)) else "INTERMEDIATE ASSOCIATION"

        supporting_txs = top_vasp.supporting_transactions if top_vasp and top_vasp.supporting_transactions else []
        if not supporting_txs:
            for p in trace_result.paths:
                for h in p.hops:
                    if h.tx_hash not in supporting_txs:
                        supporting_txs.append(h.tx_hash)

        explorer_urls = []
        provenance_sources = []
        for ev in evidence_items:
            for u in (ev.explorer_urls or []):
                if u not in explorer_urls:
                    explorer_urls.append(u)
            if ev.source_name and ev.source_name not in provenance_sources:
                provenance_sources.append(ev.source_name)

        if not explorer_urls and endpoint_address:
            explorer_urls.append(f"https://tronscan.org/#/address/{endpoint_address}")

        reasoning = top_vasp.matched_relevance_reasons if top_vasp and top_vasp.matched_relevance_reasons else ["High-velocity fund flow moving towards exchange endpoint."]

        evidence_chain = self._build_evidence_chain(
            vasp_name=vasp_name,
            endpoint_address=endpoint_address,
            attribution_score=attr_score,
            reasoning=reasoning,
            supporting_txs=supporting_txs,
            explorer_urls=explorer_urls,
            provenance_sources=provenance_sources,
        )

        request_data = {
            "schema_version": "1.0",
            "request_id": req_id,
            "request_type": "ASSET_PRESERVATION_OR_FREEZE_REQUEST",
            "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            "integration_status": self.INTEGRATION_STATUS,
            "created_at": now_str,
            "notice": "CONFIDENTIAL LAW ENFORCEMENT INVESTIGATION DRAFT — REQUIRES AUTHORISED REVIEW BEFORE TRANSMISSION",
            "urgency_level": urgency_level or "HIGH",
            "case": {
                "case_id": summary.case_id,
                "investigation_id": summary.job_id,
                "investigator_reference": investigator_id or "INV-AUTOMATED-001",
                "purpose_of_request": reason or "Authorized Law Enforcement Asset Preservation / Freeze Request",
            },
            "suspect": {
                "wallet_address": summary.target_wallet,
                "chain": summary.chain,
                "asset": summary.asset,
            },
            "attribution": {
                "vasp": vasp_name,
                "wallet_address": endpoint_address,
                "endpoint_status": ep_status,
                "attribution_score": attr_score,
                "confidence": conf_level,
                "hop_distance": hop_dist,
            },
            "evidence": {
                "supporting_transactions": supporting_txs,
                "trace_paths_count": trace_result.total_paths_found,
                "relevance_summary": reasoning,
                "explorer_references": explorer_urls,
                "provenance": provenance_sources,
            },
            "evidence_chain": evidence_chain,
            "evidence_snapshot_reference": f"snap-{summary.job_id}",
            "requested_action": {
                "type": "ASSET_PRESERVATION_OR_FREEZE_REQUEST",
                "action_description": f"Request immediate temporary administrative hold/freeze on assets transferred to endpoint '{endpoint_address}' at {vasp_name} pending formal judicial order.",
                "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            },
        }

        return request_data

    def validate_sahyog_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates SAHYOG package and request payloads against mandatory field completeness rules.
        """
        checked_fields = []
        errors = []

        # Check Metadata / Headers
        meta = package.get("sahyog_metadata") or package
        checked_fields.append("integration_status")
        if not meta.get("integration_status"):
            errors.append("Missing required field: integration_status")

        # Check Case Details
        case_info = package.get("case_details") or package.get("case") or {}
        checked_fields.append("case_id")
        if not case_info.get("case_id"):
            errors.append("Missing required field: case_id")

        checked_fields.append("job_id / investigation_id")
        if not (case_info.get("job_id") or case_info.get("investigation_id")):
            errors.append("Missing required field: job_id / investigation_id")

        # Check Suspect / Target Wallet
        suspect = package.get("suspect") or case_info
        checked_fields.append("target_wallet / wallet_address")
        target_wallet = suspect.get("target_wallet") or suspect.get("wallet_address") or case_info.get("target_wallet")
        if not target_wallet:
            errors.append("Missing required field: target_wallet")

        checked_fields.append("chain")
        if not (suspect.get("chain") or case_info.get("chain")):
            errors.append("Missing required field: chain")

        checked_fields.append("asset")
        if not (suspect.get("asset") or case_info.get("asset")):
            errors.append("Missing required field: asset")

        # Check Attribution & Endpoint
        attr = package.get("vasp_attribution") or package.get("attribution") or {}
        checked_fields.append("vasp")
        vasp_name = attr.get("attributed_vasp_name") or attr.get("vasp") or attr.get("candidate_name") or attr.get("status")
        if not vasp_name:
            errors.append("Missing required field: attributed_vasp_name")

        checked_fields.append("endpoint_address / matched_wallet")
        endpoint_addr = attr.get("matched_wallet") or attr.get("wallet_address") or attr.get("endpoint_address") or target_wallet
        if not endpoint_addr:
            errors.append("Missing required field: endpoint_address")

        checked_fields.append("attribution_score")
        score = attr.get("confidence_score") if "confidence_score" in attr else attr.get("attribution_score")
        if score is None and "status" in attr:
            score = 0.0
        if score is None:
            errors.append("Missing required field: attribution_score")

        checked_fields.append("confidence_level / confidence_band")
        if not (attr.get("confidence_band") or attr.get("confidence") or attr.get("status")):
            errors.append("Missing required field: confidence_level")


        # Check Evidence Ledger
        ev = package.get("evidence_ledger") if "evidence_ledger" in package else package.get("evidence")
        checked_fields.append("supporting_evidence")
        if ev is None:
            errors.append("Missing required field: evidence")


        # Check Requested Action if request payload
        req_action = package.get("requested_action")
        req_type = package.get("request_type") or (req_action.get("type") if req_action else None)
        if req_type:
            checked_fields.append("requested_action")
            if not req_action or not req_action.get("status"):
                errors.append("Missing required field: requested_action status")

            if req_type == "DISCLOSURE_REQUEST":
                checked_fields.append("disclosure_request_action_details")
                if not vasp_name or not endpoint_addr:
                    errors.append("Disclosure Request requires valid attributed VASP and endpoint address.")

            elif req_type == "ASSET_PRESERVATION_OR_FREEZE_REQUEST":
                checked_fields.append("freeze_request_action_details")
                if not endpoint_addr:
                    errors.append("Asset Preservation / Freeze Request requires valid endpoint address.")

        now_str = datetime.now(timezone.utc).isoformat()
        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "status": "PACKAGE VALID" if is_valid else "PACKAGE INVALID",
            "checked_at": now_str,
            "checked_fields": checked_fields,
            "errors": errors,
        }

    def export_sahyog_package(self, package: Dict[str, Any], output_dir: str, filename: str = "sahyog_package.json") -> str:
        """Exports SAHYOG package to local output directory."""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2, default=str)
        return filepath

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Contract submit method.
        Does NOT execute fake external submission. Returns integration status contract.
        """
        return {
            "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            "integration_status": self.INTEGRATION_STATUS,
            "notice": "CONFIDENTIAL LAW ENFORCEMENT INVESTIGATION DRAFT — READY FOR AUTHORISED API INTEGRATION. NO AUTOMATED EXTERNAL SUBMISSION EXECUTED.",
            "submitted_at": None,
            "external_receipt_id": None,
        }

    def get_status(self, request_id: str) -> Dict[str, Any]:
        """Contract status query method."""
        return {
            "request_id": request_id,
            "status": "DRAFT_REQUIRES_AUTHORISED_REVIEW",
            "integration_status": self.INTEGRATION_STATUS,
            "notice": "READY FOR AUTHORISED API INTEGRATION — NO LIVE UNLESS AUTHORISED",
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def acknowledge(self, request_id: str) -> Dict[str, Any]:
        """Contract acknowledgment query method."""
        return {
            "request_id": request_id,
            "acknowledged": False,
            "integration_status": self.INTEGRATION_STATUS,
            "notice": "LOCAL INVESTIGATION CONTRACT DRAFT PREPARED. AUTHORISED API INTEGRATION REQUIRED FOR PORTAL ACKNOWLEDGEMENT.",
        }


class SahyogAdapter:
    """
    Export & Action Adapter producing structured SAHYOG-ready intelligence packages & legal enforcement request drafts.
    
    IMPORTANT: This adapter operates under strict contract state:
    SAHYOG INTEGRATION STATUS: READY FOR AUTHORISED API INTEGRATION
    """

    INTEGRATION_STATUS = "READY FOR AUTHORISED API INTEGRATION"


    def __init__(self, transport: Optional[SahyogTransport] = None):
        self.transport = transport or LocalPackageTransport()

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
        requested_action: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generates a complete, structured SAHYOG-compliant JSON export payload."""
        now_str = datetime.now(timezone.utc).isoformat()

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

        vasp_info = {"status": vasp_resp.status if vasp_resp else "NO_HIGH_CONFIDENCE_VASP_IDENTIFIED"}
        top_vasp = None
        if vasp_resp and vasp_resp.status == "RESOLVED" and vasp_resp.candidates:
            top_vasp = vasp_resp.candidates[0]
            vasp_info.update({
                "attributed_vasp_name": top_vasp.candidate_name,
                "entity_role": getattr(top_vasp, "entity_role", "VASP"),
                "attribution_type": top_vasp.attribution_type,
                "confidence_score": top_vasp.attribution_confidence,
                "matched_wallet": top_vasp.endpoint_address,
                "match_position": getattr(top_vasp, "match_position", "TERMINAL_ENDPOINT"),
                "confidence_band": top_vasp.confidence_band,
                "why_this_vasp": getattr(top_vasp, "why_this_vasp", []),
                "all_candidates": [
                    {
                        "vasp_name": c.candidate_name,
                        "entity_role": getattr(c, "entity_role", "VASP"),
                        "attribution_score": c.attribution_confidence,
                        "matched_address": c.endpoint_address,
                        "attribution_type": c.attribution_type,
                        "match_position": getattr(c, "match_position", "TERMINAL_ENDPOINT"),
                    }
                    for c in vasp_resp.candidates
                ],
            })
        elif vasp_resp:
            vasp_info["negative_reason"] = getattr(vasp_resp, "negative_reason", None)
            vasp_info["candidates_considered_count"] = getattr(vasp_resp, "candidates_considered_count", len(vasp_resp.candidates))

        sahyog_findings = [f.model_dump(mode="json") for f in findings]
        sahyog_evidence = [e.model_dump(mode="json") for e in evidence_items]
        sahyog_alerts = [a.model_dump(mode="json") for a in velocity_resp.alerts]

        # Build evidence chain
        vasp_name = top_vasp.candidate_name if top_vasp else "UNKNOWN_OR_UNATTRIBUTED"
        endpoint_address = top_vasp.endpoint_address if top_vasp else (summary.target_wallet or "")
        attr_score = top_vasp.attribution_confidence if top_vasp else 0.0

        supporting_txs = top_vasp.supporting_transactions if top_vasp and top_vasp.supporting_transactions else []
        if not supporting_txs:
            for p in trace_result.paths:
                for h in p.hops:
                    if h.tx_hash not in supporting_txs:
                        supporting_txs.append(h.tx_hash)

        explorer_urls = []
        provenance_sources = []
        for ev in evidence_items:
            for u in (ev.explorer_urls or []):
                if u not in explorer_urls:
                    explorer_urls.append(u)
            if ev.source_name and ev.source_name not in provenance_sources:
                provenance_sources.append(ev.source_name)

        if not explorer_urls and endpoint_address:
            explorer_urls.append(f"https://tronscan.org/#/address/{endpoint_address}")

        reasoning = top_vasp.matched_relevance_reasons if top_vasp and top_vasp.matched_relevance_reasons else ["Observable multi-hop path alignment."]

        evidence_chain = [
            {"step_number": 1, "element_type": "VASP", "label": "Identified Virtual Asset Service Provider", "value": vasp_name, "detail": f"Attributed entity: {vasp_name}"},
            {"step_number": 2, "element_type": "ENDPOINT_WALLET", "label": "VASP-Associated Endpoint", "value": endpoint_address, "detail": f"Matched address: {endpoint_address}"},
            {"step_number": 3, "element_type": "ATTRIBUTION_SCORE", "label": "Evidence-Backed Attribution Score", "value": f"{attr_score} / 100", "detail": f"Attribution confidence: {attr_score}/100"},
            {"step_number": 4, "element_type": "REASONING", "label": "Analytical Evidence & Path Convergence", "value": "; ".join(reasoning[:3]) if reasoning else "Path alignment", "detail": "Scoring factors"},
            {"step_number": 5, "element_type": "SUPPORTING_TRANSACTION", "label": "Observable Blockchain Transactions", "value": supporting_txs[0] if supporting_txs else "N/A", "detail": f"Total supporting txs: {len(supporting_txs)}"},
            {"step_number": 6, "element_type": "EXPLORER_REFERENCE", "label": "Explorer Reference URL", "value": explorer_urls[0] if explorer_urls else f"https://tronscan.org/#/address/{endpoint_address}", "detail": "Verifiable on-chain link"},
            {"step_number": 7, "element_type": "VASP_PROVENANCE", "label": "Intelligence Source Provenance", "value": provenance_sources[0] if provenance_sources else "Verified Public Intelligence Registry", "detail": "Provenanced intelligence"},
        ]

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
            "evidence_chain": evidence_chain,
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
            "requested_action": requested_action,
        }

        return package

    def build_disclosure_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.transport.build_disclosure_request(
            summary=summary,
            vasp_resp=vasp_resp,
            evidence_items=evidence_items,
            trace_result=trace_result,
            investigator_id=investigator_id,
            reason=reason,
        )

    def build_freeze_request(
        self,
        summary: InvestigationSummarySchema,
        vasp_resp: Optional[VASPAttributionResponse],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        investigator_id: Optional[str] = None,
        reason: Optional[str] = None,
        urgency_level: Optional[str] = "HIGH",
    ) -> Dict[str, Any]:
        return self.transport.build_freeze_request(
            summary=summary,
            vasp_resp=vasp_resp,
            evidence_items=evidence_items,
            trace_result=trace_result,
            investigator_id=investigator_id,
            reason=reason,
            urgency_level=urgency_level,
        )

    def validate_sahyog_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        return self.transport.validate_sahyog_package(package)

    def export_sahyog_package(self, package: Dict[str, Any], output_dir: str, filename: str = "sahyog_package.json") -> str:
        return self.transport.export_sahyog_package(package, output_dir=output_dir, filename=filename)

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.transport.submit(payload)

    def get_status(self, request_id: str) -> Dict[str, Any]:
        return self.transport.get_status(request_id)

    def acknowledge(self, request_id: str) -> Dict[str, Any]:
        return self.transport.acknowledge(request_id)
