import os
import csv
import json
import logging
from typing import Dict, Any, List
from app.schemas.trace import TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.risk import RiskIndicatorResponse
from app.schemas.vasp import VASPAttributionResponse
from app.schemas.investigation import FindingSchema, EvidenceGraphItemSchema, InvestigationSummarySchema

logger = logging.getLogger("specter.export.exporters")


class DataExporter:
    """
    Exports investigation results into structured JSON and CSV datasets:
    - investigation_result.json
    - transactions.csv
    - trace_edges.csv
    - trace_paths.csv
    - vasp_candidates.csv
    - evidence.csv
    - alerts.csv
    """

    def export_all(
        self,
        output_dir: str,
        summary: InvestigationSummarySchema,
        findings: List[FindingSchema],
        evidence_items: List[EvidenceGraphItemSchema],
        trace_result: TraceResultResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        risk_resp: RiskIndicatorResponse,
        vasp_resp: VASPAttributionResponse,
        sahyog_package: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        Exports all investigation datasets into the specified directory.
        Returns a dict of filename -> absolute path.
        """
        os.makedirs(output_dir, exist_ok=True)
        generated_files = {}

        # 1. investigation_result.json
        json_path = os.path.join(output_dir, "investigation_result.json")
        result_payload = {
            "summary": summary.model_dump(mode="json"),
            "risk_indicator": risk_resp.model_dump(mode="json"),
            "vasp_attribution": vasp_resp.model_dump(mode="json") if vasp_resp else {},
            "findings": [f.model_dump(mode="json") for f in findings],
            "evidence": [e.model_dump(mode="json") for e in evidence_items],
            "velocity_analysis": velocity_resp.model_dump(mode="json"),
            "typology_analysis": typology_resp.model_dump(mode="json"),
            "trace_result": trace_result.model_dump(mode="json"),
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2, default=str)
        generated_files["investigation_result.json"] = json_path

        # 2. sahyog_package.json
        sahyog_path = os.path.join(output_dir, "sahyog_package.json")
        with open(sahyog_path, "w", encoding="utf-8") as f:
            json.dump(sahyog_package, f, indent=2, default=str)
        generated_files["sahyog_package.json"] = sahyog_path

        # 3. transactions.csv / trace_edges.csv
        edges_path = os.path.join(output_dir, "trace_edges.csv")
        tx_path = os.path.join(output_dir, "transactions.csv")
        
        tx_rows = []
        for path in trace_result.paths:
            for hop in path.hops:
                tx_rows.append({
                    "tx_hash": hop.tx_hash,
                    "from_address": hop.from_address,
                    "to_address": hop.to_address,
                    "asset": hop.asset,
                    "amount": hop.amount,
                    "hop_number": hop.hop_number,
                    "timestamp": hop.timestamp,
                    "delta_t_seconds": hop.delta_t_seconds,
                    "explorer_url": hop.explorer_url,
                })
        
        # Write trace_edges.csv
        with open(edges_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["tx_hash", "from_address", "to_address", "asset", "amount", "hop_number", "timestamp", "delta_t_seconds", "explorer_url"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tx_rows)
        generated_files["trace_edges.csv"] = edges_path

        # Write transactions.csv
        with open(tx_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(tx_rows)
        generated_files["transactions.csv"] = tx_path

        # 4. trace_paths.csv
        paths_csv_path = os.path.join(output_dir, "trace_paths.csv")
        path_rows = []
        for p in trace_result.paths:
            path_rows.append({
                "path_id": p.path_id,
                "hop_count": p.hop_count,
                "starting_wallet": p.wallet_sequence[0] if p.wallet_sequence else "",
                "destination_wallet": p.wallet_sequence[-1] if p.wallet_sequence else "",
                "initial_amount": p.initial_amount,
                "final_amount": p.final_amount,
                "value_retention_percent": p.value_retention_percent,
                "elapsed_time_seconds": p.elapsed_time_seconds,
                "relevance_score": p.relevance_score,
                "wallet_sequence": " -> ".join(p.wallet_sequence),
            })
        with open(paths_csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["path_id", "hop_count", "starting_wallet", "destination_wallet", "initial_amount", "final_amount", "value_retention_percent", "elapsed_time_seconds", "relevance_score", "wallet_sequence"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(path_rows)
        generated_files["trace_paths.csv"] = paths_csv_path

        # 5. vasp_candidates.csv
        vasp_csv_path = os.path.join(output_dir, "vasp_candidates.csv")
        vasp_rows = []
        if vasp_resp and vasp_resp.candidates:
            for c in vasp_resp.candidates:
                vasp_rows.append({
                    "vasp_name": c.candidate_name,
                    "matched_address": c.endpoint_address,
                    "attribution_type": c.attribution_type,
                    "label_type": c.confidence_band,
                    "attribution_score": c.attribution_confidence,
                    "confidence": c.source_confidence,
                    "is_known_exchange": True,
                })
        with open(vasp_csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["vasp_name", "matched_address", "attribution_type", "label_type", "attribution_score", "confidence", "is_known_exchange"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vasp_rows)
        generated_files["vasp_candidates.csv"] = vasp_csv_path

        # 6. evidence.csv
        ev_csv_path = os.path.join(output_dir, "evidence.csv")
        ev_rows = []
        for e in evidence_items:
            ev_rows.append({
                "evidence_id": e.evidence_id,
                "finding_id": e.finding_id or "",
                "evidence_type": e.evidence_type,
                "finding": e.finding,
                "confidence": e.confidence,
                "source_name": e.source_name,
                "supporting_tx_count": len(e.supporting_tx_hashes),
                "supporting_addresses_count": len(e.supporting_addresses),
                "retrieval_timestamp": e.retrieval_timestamp.isoformat() if hasattr(e.retrieval_timestamp, "isoformat") else str(e.retrieval_timestamp),
            })
        with open(ev_csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["evidence_id", "finding_id", "evidence_type", "finding", "confidence", "source_name", "supporting_tx_count", "supporting_addresses_count", "retrieval_timestamp"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ev_rows)
        generated_files["evidence.csv"] = ev_csv_path

        # 7. alerts.csv
        alerts_csv_path = os.path.join(output_dir, "alerts.csv")
        alert_rows = []
        for a in velocity_resp.alerts:
            alert_rows.append({
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "velocity_score": a.velocity_score,
                "transfer_count": a.transfer_count,
                "total_amount": a.total_amount,
                "minimum_delta_t": a.minimum_delta_t,
                "average_delta_t": a.average_delta_t,
                "reason_codes": "|".join(a.reason_codes),
                "explanation": a.explanation,
            })
        with open(alerts_csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["alert_id", "alert_type", "severity", "velocity_score", "transfer_count", "total_amount", "minimum_delta_t", "average_delta_t", "reason_codes", "explanation"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(alert_rows)
        generated_files["alerts.csv"] = alerts_csv_path

        return generated_files
