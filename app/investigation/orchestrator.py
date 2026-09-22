import os
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.investigation import InvestigationJob, InvestigationSnapshot
from app.models.finding import Finding
from app.models.evidence import EvidenceItem
from app.schemas.investigation import (
    InvestigationState,
    InvestigationStartRequest,
    InvestigationJobResponse,
    FindingSchema,
    EvidenceGraphItemSchema,
    InvestigationSummarySchema,
    InvestigationSnapshotSchema,
)
from app.schemas.trace import TraceRequest, TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse

from app.blockchain.registry import ChainRegistry
from app.tracing.engine import TraceEngine

from app.velocity.service import VelocityService
from app.typologies.service import TypologyService
from app.risk.service import RiskService
from app.vasp.service import VASPService
from app.evidence.builder import EvidenceBuilder
from app.reporting.pdf_generator import PDFReportGenerator
from app.sahyog.adapter import SahyogAdapter
from app.export.exporters import DataExporter

logger = logging.getLogger("specter.investigation.orchestrator")


class InvestigationOrchestrator:
    """
    Single entry-point pipeline orchestrator for Specter automated blockchain investigations.
    Manages the 13-stage state machine, parameter snapshots, analytical engines execution,
    evidence graph building, PDF report generation, and SAHYOG package creation.
    """

    def __init__(self, db: Session):
        self.db = db
        self.trace_engine = TraceEngine(db)
        self.velocity_service = VelocityService(db)
        self.typology_service = TypologyService(db)
        self.risk_service = RiskService(db)
        self.vasp_service = VASPService(db)
        self.evidence_builder = EvidenceBuilder(db)
        self.pdf_generator = PDFReportGenerator()
        self.sahyog_adapter = SahyogAdapter()
        self.data_exporter = DataExporter()

    async def execute_investigation(
        self,
        request: InvestigationStartRequest,
        case_id: Optional[str] = None,
        export_dir: Optional[str] = None,
    ) -> Tuple[InvestigationJobResponse, InvestigationSummarySchema, Dict[str, Any]]:
        """
        Executes complete end-to-end investigation workflow for a target wallet.
        """
        t0 = time.time()
        stage_timings: Dict[str, float] = {}

        # Ensure Case record exists
        eff_case_id = case_id or f"case-{uuid.uuid4().hex[:8]}"
        case = self.db.query(Case).filter(Case.case_id == eff_case_id).first()
        if not case:
            case = Case(
                case_id=eff_case_id,
                investigator_id=request.investigator_id or "INV-AUTOMATED-001",
                reported_wallet=request.wallet,
                chain=request.chain,
                asset=request.asset,
                description=request.description,
            )
            self.db.add(case)
            self.db.commit()

        # Create InvestigationJob record
        job_id = f"job-{uuid.uuid4().hex[:10]}"
        parameters_snapshot = {
            "target_wallet": request.wallet,
            "chain": request.chain,
            "asset": request.asset,
            "max_hops": request.max_hops,
            "min_transfer_amount": request.min_transfer_amount,
            "velocity_thresholds": {"window_sizes": ["1m", "5m", "10m", "30m", "1h"], "min_delta_t_alert": 60.0},
            "typology_thresholds": {"peel_ratio_max": 0.3, "fanout_min_branches": 3},
            "scoring_model_version": "v1.0",
            "source_intelligence_version": "v1.0.2026",
            "engine_version": "1.0.0",
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        job = InvestigationJob(
            job_id=job_id,
            case_id=eff_case_id,
            target_wallet=request.wallet,
            chain=request.chain,
            asset=request.asset,
            status=InvestigationState.QUEUED.value,
            progress_percent=0.0,
            current_stage="QUEUED",
            parameters_snapshot=parameters_snapshot,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        self.db.commit()

        try:
            # Stage 1: VALIDATING (5%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.VALIDATING, 5.0)
            clean_wallet = request.wallet.strip() if request.wallet else ""
            if not clean_wallet or len(clean_wallet) < 10:
                raise ValueError(f"Invalid target wallet address '{request.wallet}'. Address is empty or too short.")
            if not ChainRegistry.validate_address_for_chain(request.chain, clean_wallet):
                raise ValueError(f"Invalid {request.chain} target wallet address '{request.wallet}'. Address syntax check failed.")

            stage_timings["VALIDATING"] = round(time.time() - t_stage, 3)

            # Stage 2: INGESTING (15%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.INGESTING, 15.0)
            stage_timings["INGESTING"] = round(time.time() - t_stage, 3)

            # Stage 3: TRACING (35%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.TRACING, 35.0)
            trace_req = TraceRequest(
                starting_wallet=request.wallet,
                chain=request.chain,
                asset=request.asset,
                max_hops=request.max_hops,
                min_transfer_amount=request.min_transfer_amount,
            )
            trace_result = await self.trace_engine.execute_trace(request=trace_req, case_id=eff_case_id)
            stage_timings["TRACING"] = round(time.time() - t_stage, 3)

            # Stage 4: GRAPH_ANALYSIS (50%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.GRAPH_ANALYSIS, 50.0)
            # Create reproducible snapshot of trace graph
            graph_snapshot = trace_result.model_dump(mode="json")
            db_snapshot = InvestigationSnapshot(
                snapshot_id=f"snap-{uuid.uuid4().hex[:8]}",
                job_id=job_id,
                case_id=eff_case_id,
                target_wallet=request.wallet,
                chain=request.chain,
                asset=request.asset,
                parameters=parameters_snapshot,
                trace_graph_snapshot=graph_snapshot,
                engine_version="1.0.0",
                scoring_model_version="v1.0",
                source_intelligence_version="v1.0.2026",
            )
            self.db.add(db_snapshot)
            self.db.commit()
            stage_timings["GRAPH_ANALYSIS"] = round(time.time() - t_stage, 3)

            # Stage 5: PATTERN_ANALYSIS (65%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.PATTERN_ANALYSIS, 65.0)
            velocity_resp = self.velocity_service.analyze_trace(trace_result, case_id=eff_case_id)
            typology_resp = self.typology_service.analyze_trace(trace_result, case_id=eff_case_id)
            risk_resp = self.risk_service.analyze_trace(trace_result, case_id=eff_case_id)
            stage_timings["PATTERN_ANALYSIS"] = round(time.time() - t_stage, 3)

            # Stage 6: VASP_RESOLUTION (80%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.VASP_RESOLUTION, 80.0)
            vasp_resp = None
            try:
                vasp_resp = self.vasp_service.resolve_from_trace_result(trace_result, case_id=eff_case_id)
            except Exception as ve:
                logger.warning(f"VASP resolution notice for job {job_id}: {ve}")
            stage_timings["VASP_RESOLUTION"] = round(time.time() - t_stage, 3)

            # Stage 7: EVIDENCE_BUILDING (90%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.EVIDENCE_BUILDING, 90.0)
            findings, evidence_items = self.evidence_builder.build_evidence_graph_and_findings(
                case_id=eff_case_id,
                job_id=job_id,
                trace_result=trace_result,
                velocity_resp=velocity_resp,
                typology_resp=typology_resp,
                risk_resp=risk_resp,
                vasp_resp=vasp_resp,
            )
            stage_timings["EVIDENCE_BUILDING"] = round(time.time() - t_stage, 3)

            # Stage 8: REPORT_GENERATION (95%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.REPORT_GENERATION, 95.0)
            target_export_dir = export_dir or os.path.join("exports", eff_case_id)
            pdf_path = os.path.join(target_export_dir, "investigation_report.pdf")
            self.pdf_generator.generate_pdf_report(
                output_path=pdf_path,
                summary=self._build_summary_object(
                    eff_case_id, job_id, request, trace_result, risk_resp, velocity_resp, typology_resp, vasp_resp, findings, evidence_items, time.time() - t0
                ),
                findings=findings,
                evidence_items=evidence_items,
                trace_result=trace_result,
                velocity_resp=velocity_resp,
                typology_resp=typology_resp,
                risk_resp=risk_resp,
                vasp_resp=vasp_resp,
            )
            stage_timings["REPORT_GENERATION"] = round(time.time() - t_stage, 3)

            # Stage 9: PACKAGE_GENERATION (98%)
            t_stage = time.time()
            self._update_job_stage(job, InvestigationState.PACKAGE_GENERATION, 98.0)
            summary_obj = self._build_summary_object(
                eff_case_id, job_id, request, trace_result, risk_resp, velocity_resp, typology_resp, vasp_resp, findings, evidence_items, time.time() - t0
            )

            sahyog_pkg = self.sahyog_adapter.build_sahyog_package(
                summary=summary_obj,
                findings=findings,
                evidence_items=evidence_items,
                trace_result=trace_result,
                velocity_resp=velocity_resp,
                typology_resp=typology_resp,
                risk_resp=risk_resp,
                vasp_resp=vasp_resp,
            )

            # Export all files (JSON, CSVs, SAHYOG package)
            self.data_exporter.export_all(
                output_dir=target_export_dir,
                summary=summary_obj,
                findings=findings,
                evidence_items=evidence_items,
                trace_result=trace_result,
                velocity_resp=velocity_resp,
                typology_resp=typology_resp,
                risk_resp=risk_resp,
                vasp_resp=vasp_resp,
                sahyog_package=sahyog_pkg,
            )
            stage_timings["PACKAGE_GENERATION"] = round(time.time() - t_stage, 3)

            # Stage 10: COMPLETED (100%)
            total_duration = round(time.time() - t0, 3)
            self._update_job_stage(job, InvestigationState.COMPLETED, 100.0)
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()

            job_resp = InvestigationJobResponse.model_validate(job)
            return job_resp, summary_obj, sahyog_pkg

        except Exception as e:
            logger.exception(f"Investigation execution failed for job {job_id}: {e}")
            try:
                self.db.rollback()
                job.status = InvestigationState.FAILED.value
                job.current_stage = "FAILED"
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
            except Exception as rollback_err:
                logger.error(f"Failed to record job failure in DB for {job_id}: {rollback_err}")
            raise e

    def _update_job_stage(self, job: InvestigationJob, state: InvestigationState, progress: float):
        job.status = state.value
        job.current_stage = state.value
        job.progress_percent = progress
        self.db.commit()

    def _build_summary_object(
        self,
        case_id: str,
        job_id: str,
        request: InvestigationStartRequest,
        trace_result: TraceResultResponse,
        risk_resp: RiskIndicatorResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        vasp_resp: Optional[VASPAttributionResponse],
        findings: List[FindingSchema],
        evidence_items: List[EvidenceGraphItemSchema],
        duration_seconds: float,
    ) -> InvestigationSummarySchema:
        vasp_dict = {}
        if vasp_resp and vasp_resp.candidates:
            top_v = vasp_resp.candidates[0]
            vasp_dict = {
                "attributed_vasp": top_v.candidate_name,
                "attribution_type": top_v.attribution_type,
                "confidence": top_v.attribution_confidence,
                "matched_address": top_v.endpoint_address,
            }

        return InvestigationSummarySchema(
            case_id=case_id,
            job_id=job_id,
            target_wallet=request.wallet,
            chain=request.chain,
            asset=request.asset,
            investigation_status="COMPLETED",
            risk_score=risk_resp.risk_score,
            raw_risk_score=risk_resp.raw_risk_score,
            contextual_risk_score=risk_resp.contextual_risk_score,
            risk_level=risk_resp.risk_level,
            is_known_service_entity=risk_resp.is_known_service_entity,
            service_entity_context=risk_resp.service_entity_context,
            contextual_interpretation=risk_resp.contextual_interpretation,
            total_wallets_traced=trace_result.total_wallets_discovered,
            total_transactions_analyzed=trace_result.total_transactions_analyzed,
            total_paths_found=trace_result.total_paths_found,
            vasp_resolution=vasp_dict,
            findings_summary=[{"title": f.title, "severity": f.severity, "type": f.finding_type} for f in findings],
            velocity_alerts_count=len(velocity_resp.alerts),
            typologies_detected_count=len(typology_resp.typologies),
            evidence_count=len(evidence_items),
            execution_duration_seconds=round(duration_seconds, 2),
            completed_at=datetime.now(timezone.utc),
        )

    def get_job(self, job_id: str) -> Optional[InvestigationJobResponse]:
        job = self.db.query(InvestigationJob).filter(InvestigationJob.job_id == job_id).first()
        if not job:
            return None
        return InvestigationJobResponse.model_validate(job)

    def get_findings(self, case_id: str) -> List[FindingSchema]:
        db_fnds = self.db.query(Finding).filter(Finding.case_id == case_id).all()
        result = []
        for f in db_fnds:
            result.append(
                FindingSchema(
                    finding_id=f.finding_id,
                    case_id=f.case_id,
                    job_id=f.job_id,
                    finding_type=f.finding_type,
                    title=f.title,
                    description=f.description,
                    severity=f.severity,
                    confidence=f.confidence,
                    supporting_evidence_ids=f.supporting_evidence_ids or [],
                    metadata=f.metadata_json or {},
                    created_at=f.created_at,
                )
            )
        return result

    def get_evidence(self, case_id: str) -> List[EvidenceGraphItemSchema]:
        db_evs = self.db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()
        result = []
        for ev in db_evs:
            result.append(
                EvidenceGraphItemSchema(
                    evidence_id=f"ev-{ev.id}",
                    case_id=ev.case_id,
                    evidence_type="EVIDENCE_ITEM",
                    finding=ev.finding,
                    supporting_tx_hashes=ev.supporting_tx_hashes or [],
                    supporting_addresses=ev.supporting_addresses or [],
                    supporting_path_ids=[],
                    source_name=ev.source,
                    explorer_urls=ev.explorer_urls or [],
                    confidence=ev.confidence,
                    retrieval_timestamp=ev.retrieval_timestamp,
                    scoring_factors=ev.scoring_factors or {},
                )
            )
        return result
