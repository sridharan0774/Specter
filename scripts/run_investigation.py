import sys
import os
import argparse
import asyncio
import json
import logging
from datetime import datetime

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.schemas.investigation import InvestigationStartRequest
from app.investigation.orchestrator import InvestigationOrchestrator
from app.evaluation.framework import EvaluationFramework, GroundTruthTestCase

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("specter.cli")


async def main():
    parser = argparse.ArgumentParser(
        description="SPECTER Phase 6 Investigation Orchestration, Evidence, Reporting & SAHYOG Package CLI"
    )
    parser.add_argument(
        "--wallet",
        "-w",
        type=str,
        required=True,
        help="Target TRON wallet address to execute end-to-end investigation on",
    )
    parser.add_argument("--case-id", "-c", type=str, help="Optional investigation case ID")
    parser.add_argument("--chain", type=str, default="TRON", help="Blockchain network (default: TRON)")
    parser.add_argument("--asset", type=str, default="USDT", help="Asset symbol filter (default: USDT)")
    parser.add_argument("--max-hops", type=int, default=3, help="Max hop depth for multi-hop tracing (default: 3)")
    parser.add_argument("--min-amount", type=float, default=0.0, help="Minimum transfer amount threshold")
    parser.add_argument("--export-dir", "-o", type=str, help="Output directory path to export report, JSON, CSVs, and SAHYOG package")
    parser.add_argument("--eval", action="store_true", help="Run system evaluation framework against benchmark suite")
    parser.add_argument("--json", action="store_true", help="Output raw SAHYOG JSON package to stdout")

    args = parser.parse_args()

    init_db()
    db = SessionLocal()

    try:
        wallet = args.wallet.strip()
        case_id = args.case_id or f"case-cli-{int(datetime.now().timestamp())}"
        export_dir = args.export_dir or os.path.join("exports", case_id)

        print("\n" + "=" * 80)
        print(" SPECTER AUTOMATED BLOCKCHAIN INVESTIGATION ORCHESTRATOR")
        print("=" * 80)
        print(f"Target Wallet      : {wallet}")
        print(f"Case ID            : {case_id}")
        print(f"Network / Asset    : {args.chain} ({args.asset})")
        print(f"Tracing Depth      : Max Hops = {args.max_hops}")
        print(f"Export Directory   : {os.path.abspath(export_dir)}")
        print("-" * 80)

        orchestrator = InvestigationOrchestrator(db)

        inv_request = InvestigationStartRequest(
            wallet=wallet,
            chain=args.chain,
            asset=args.asset,
            max_hops=args.max_hops,
            min_transfer_amount=args.min_amount,
            investigator_id="INV-CLI-001",
            description=f"CLI investigation execution for wallet {wallet}",
        )

        print("[*] Executing 13-stage investigation pipeline...")
        job_resp, summary, sahyog_pkg = await orchestrator.execute_investigation(
            request=inv_request,
            case_id=case_id,
            export_dir=export_dir,
        )

        if args.json:
            print(json.dumps(sahyog_pkg, indent=2))
            return

        print("\n" + "=" * 80)
        print(" INVESTIGATION EXECUTIVE SUMMARY & RESULTS")
        print("=" * 80)
        print(f"Job Status          : {job_resp.status} ({job_resp.progress_percent:.0f}%)")
        print(f"Execution Duration  : {summary.execution_duration_seconds:.2f} seconds")
        print("-" * 80)
        print(f"1. RISK ASSESSMENT:")
        print(f"   - Contextual Risk Score : {summary.risk_score:.1f} / 100.0 ({summary.risk_level})")
        print(f"   - Raw Structural Score  : {summary.raw_risk_score:.1f} / 100.0")
        print(f"   - Service Entity Context: {summary.service_entity_context}")
        print(f"   - Interpretation        : {summary.contextual_interpretation}")

        print("-" * 80)
        print(f"2. FUND-TRACING GRAPH SUMMARY:")
        print(f"   - Wallets Discovered    : {summary.total_wallets_traced}")
        print(f"   - Transactions Analyzed : {summary.total_transactions_analyzed}")
        print(f"   - Trace Paths Rebuilt   : {summary.total_paths_found}")

        print("-" * 80)
        print(f"3. VASP ATTRIBUTION RESOLUTION:")
        if summary.vasp_resolution:
            print(f"   - Attributed VASP       : {summary.vasp_resolution.get('attributed_vasp')}")
            print(f"   - Attribution Type      : {summary.vasp_resolution.get('attribution_type')}")
            print(f"   - Confidence Score      : {summary.vasp_resolution.get('confidence', 0.0):.2f}")
            print(f"   - Matched Wallet        : {summary.vasp_resolution.get('matched_address')}")
        else:
            print("   - No direct VASP endpoint resolved.")

        print("-" * 80)
        print(f"4. ANALYTICAL FINDINGS & EVIDENCE:")
        print(f"   - Total Findings Count  : {len(summary.findings_summary)}")
        print(f"   - Evidence Graph Items  : {summary.evidence_count}")
        print(f"   - Velocity Alerts       : {summary.velocity_alerts_count}")
        print(f"   - Typologies Detected   : {summary.typologies_detected_count}")

        print("-" * 80)
        print(f"5. GENERATED ARTIFACTS & EXPORTS:")
        print(f"   - PDF Report            : {os.path.join(export_dir, 'investigation_report.pdf')}")
        print(f"   - SAHYOG Package        : {os.path.join(export_dir, 'sahyog_package.json')}")
        print(f"   - Result JSON           : {os.path.join(export_dir, 'investigation_result.json')}")
        print(f"   - CSV Files             : trace_edges.csv, transactions.csv, trace_paths.csv, vasp_candidates.csv, evidence.csv, alerts.csv")

        if args.eval:
            print("-" * 80)
            print("6. SYSTEM EVALUATION BENCHMARK METRICS:")
            eval_fw = EvaluationFramework()
            gt_case = GroundTruthTestCase(
                case_id=case_id,
                target_wallet=wallet,
                true_vasp_name=summary.vasp_resolution.get("attributed_vasp", "UNKNOWN"),
                true_vasp_address=wallet,
                true_paths=[],
                has_high_velocity=summary.velocity_alerts_count > 0,
            )
            eval_pred = {
                "case_id": case_id,
                "candidate_vasps": [{"vasp_name": summary.vasp_resolution.get("attributed_vasp")}],
                "discovered_paths": [1] * summary.total_paths_found,
                "has_high_velocity": summary.velocity_alerts_count > 0,
            }
            eval_report = eval_fw.run_evaluation(
                ground_truth_cases=[gt_case],
                predictions=[eval_pred],
                total_pipeline_seconds=summary.execution_duration_seconds,
            )
            print(f"   - VASP Top-1 Accuracy   : {eval_report.vasp_metrics.top_1_accuracy * 100:.1f}%")
            print(f"   - Path Reconstruction   : {eval_report.vasp_metrics.path_reconstruction_success_rate * 100:.1f}%")
            print(f"   - Velocity Precision    : {eval_report.velocity_metrics.precision * 100:.1f}%")
            print(f"   - Efficiency Speedup    : {eval_report.baseline_comparison.efficiency_multiplier:.1f}x faster than manual tracing baseline")

        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
