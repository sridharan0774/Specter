import sys
import os
import argparse
import asyncio
import json
from datetime import datetime

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.schemas.trace import TraceRequest
from app.tracing.engine import TraceEngine
from app.velocity.service import VelocityService
from app.typologies.service import TypologyService
from app.risk.service import RiskService


async def main():
    parser = argparse.ArgumentParser(
        description="SPECTER Phase 5 High-Velocity Detection, Typologies & Risk Intelligence CLI"
    )
    parser.add_argument("--trace-id", type=str, help="Existing multi-hop trace ID to analyze")
    parser.add_argument(
        "--wallet",
        "--starting-wallet",
        type=str,
        help="Target wallet address to trace and analyze patterns for",
    )
    parser.add_argument("--chain", type=str, default="TRON", help="Blockchain network (default: TRON)")
    parser.add_argument("--asset", type=str, default="USDT", help="Asset symbol filter (default: USDT)")
    parser.add_argument("--max-hops", type=int, default=3, help="Max hop depth for fund trace (default: 3)")
    parser.add_argument("--case-id", type=str, help="Optional investigation case ID")
    parser.add_argument("--output", type=str, help="Optional file path to save JSON report")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    args = parser.parse_args()

    if not args.trace_id and not args.wallet:
        parser.error("Must provide either --trace-id or --wallet address.")

    init_db()
    db = SessionLocal()

    try:
        v_service = VelocityService(db)
        t_service = TypologyService(db)
        r_service = RiskService(db)

        if args.trace_id:
            print(f"[*] Analyzing transaction patterns for existing Trace ID: {args.trace_id}")
            vel_res = v_service.analyze_trace_id(args.trace_id, case_id=args.case_id)
            typ_res = t_service.analyze_trace_id(args.trace_id, case_id=args.case_id)
            risk_res = r_service.analyze_trace_id(args.trace_id, case_id=args.case_id)
        else:
            starting_wallet = args.wallet.strip()
            print(
                f"[*] Executing live fund trace for wallet: {starting_wallet} ({args.chain}, asset: {args.asset}, max_hops: {args.max_hops})"
            )

            trace_req = TraceRequest(
                starting_wallet=starting_wallet,
                chain=args.chain,
                asset=args.asset,
                max_hops=args.max_hops,
                min_transfer_amount=0.0,
            )

            engine = TraceEngine(db=db)
            trace_result = await engine.execute_trace(request=trace_req, case_id=args.case_id)
            print(
                f"[+] Multi-hop trace complete. Discovered {trace_result.total_wallets_discovered} wallets across {trace_result.total_paths_found} path(s)."
            )

            print("[*] Performing velocity, typology, and risk pattern analysis...")
            vel_res = v_service.analyze_trace(trace_result, case_id=args.case_id)
            typ_res = t_service.analyze_trace(trace_result, case_id=args.case_id)
            risk_res = r_service.analyze_trace(trace_result, case_id=args.case_id)

        full_output = {
            "trace_id": vel_res.trace_id,
            "case_id": vel_res.case_id,
            "starting_wallet": vel_res.starting_wallet,
            "chain": vel_res.chain,
            "asset": vel_res.asset,
            "velocity_analysis": vel_res.model_dump(mode="json"),
            "typology_analysis": typ_res.model_dump(mode="json"),
            "risk_indicator": risk_res.model_dump(mode="json"),
        }

        if args.output:
            with open(args.output, "w") as f:
                json.dump(full_output, f, indent=2)
            print(f"[+] Full pattern analysis saved to file: {args.output}")

        if args.json:
            print(json.dumps(full_output, indent=2))
            return

        print("\n" + "=" * 80)
        print(" SPECTER HIGH-VELOCITY, TYPOLOGY & RISK INTELLIGENCE REPORT")
        print("=" * 80)
        print(f"Trace Run ID        : {vel_res.trace_id}")
        print(f"Case ID             : {vel_res.case_id or 'N/A'}")
        print(f"Starting Wallet     : {vel_res.starting_wallet}")
        print(f"Chain / Asset       : {vel_res.chain} / {vel_res.asset}")
        print("-" * 80)
        print(f"1. TRANSACTION-FLOW RISK INDICATOR:")
        print(f"   - Risk Score               : {risk_res.risk_score:.1f} / 100.0")
        print(f"   - Risk Level               : {risk_res.risk_level}")
        print(f"   - Known Service Entity     : {risk_res.is_known_service_entity}")
        print("   - Component Breakdown:")
        for comp_name, comp_val in risk_res.component_contributions.items():
            print(f"       * {comp_name}: {comp_val:.2f} pts")
        if risk_res.contributing_factors:
            print("   - Contributing Risk Factors:")
            for factor in risk_res.contributing_factors:
                print(f"       * {factor}")
        if risk_res.false_positive_mitigations:
            print("   - False Positive Mitigations Applied:")
            for mit in risk_res.false_positive_mitigations:
                print(f"       * {mit}")

        print("-" * 80)
        print(f"2. HIGH-VELOCITY MOVEMENT ANALYSIS:")
        print(f"   - High Velocity Detected   : {vel_res.has_high_velocity_pattern}")
        print(f"   - Status                   : {vel_res.status}")
        print(f"   - Summary                  : {vel_res.summary}")
        if vel_res.alerts:
            print(f"   - Triggered Velocity Alerts ({len(vel_res.alerts)} alert(s)):")
            for alert in vel_res.alerts:
                print(f"       * Alert ID: {alert.alert_id} [{alert.severity} Severity, Score: {alert.velocity_score:.1f}]")
                print(f"         Minimum delta_t: {alert.minimum_delta_t:.1f}s | Average delta_t: {alert.average_delta_t:.1f}s")
                print(f"         Reason codes: {', '.join(alert.reason_codes)}")

        print("-" * 80)
        print(f"3. TRANSACTION TYPOLOGY STRUCTURAL PATTERNS:")
        print(f"   - Summary                  : {typ_res.summary}")
        if typ_res.typologies:
            print(f"   - Detected Typologies ({len(typ_res.typologies)} pattern(s)):")
            for typ in typ_res.typologies:
                print(f"       * [{typ.typology_name}] Severity: {typ.severity} (Confidence: {typ.confidence:.2f})")
                print(f"         Description: {typ.description}")
                print(f"         Supporting Tx Count: {len(typ.supporting_transactions)}")
        else:
            print("   - No structural typologies flagged.")

        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
