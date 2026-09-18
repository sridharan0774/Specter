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
from app.vasp.service import VASPService


async def run_vasp_resolution():
    parser = argparse.ArgumentParser(description="SPECTER Phase 4 Real-Data VASP Attribution Engine CLI")
    parser.add_argument("--trace-id", type=str, help="Existing multi-hop trace ID to evaluate")
    parser.add_argument("--wallet", "--starting-wallet", type=str, help="Target wallet address to trace and resolve VASP attribution for")
    parser.add_argument("--chain", type=str, default="TRON", help="Blockchain network (default: TRON)")
    parser.add_argument("--asset", type=str, default="USDT", help="Asset symbol filter (default: USDT)")
    parser.add_argument("--max-hops", type=int, default=3, help="Max hop depth for fund flow trace (default: 3)")
    parser.add_argument("--case-id", type=str, help="Optional investigation case ID")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    args = parser.parse_args()

    if not args.trace_id and not args.wallet:
        parser.error("Must provide either --trace-id or --wallet address.")

    # Ensure DB tables are initialized
    init_db()
    db = SessionLocal()

    try:
        service = VASPService(db)

        if args.trace_id:
            print(f"[*] Evaluating VASP Attribution for existing Trace ID: {args.trace_id}")
            result = service.resolve_from_trace_id(trace_id=args.trace_id, case_id=args.case_id)
        else:
            starting_wallet = args.wallet.strip()
            print(f"[*] Executing live fund trace for wallet: {starting_wallet} ({args.chain}, asset: {args.asset}, max_hops: {args.max_hops})")
            
            trace_req = TraceRequest(
                starting_wallet=starting_wallet,
                chain=args.chain,
                asset=args.asset,
                max_hops=args.max_hops,
                min_transfer_amount=0.0,
            )
            
            engine = TraceEngine(db=db)
            trace_result = await engine.execute_trace(request=trace_req, case_id=args.case_id)
            print(f"[+] Multi-hop trace complete. Discovered {trace_result.total_wallets_discovered} wallets across {trace_result.total_paths_found} path(s).")

            print(f"[*] Resolving VASP Attribution...")
            result = service.resolve_from_trace_result(trace_result=trace_result, case_id=args.case_id)

        if args.json:
            print(json.dumps(result.model_dump(mode="json"), indent=2))
            return

        print("\n" + "=" * 80)
        print(" SPECTER VASP ATTRIBUTION REPORT")
        print("=" * 80)
        print(f"Attribution Evaluation ID : {result.attribution_id}")
        print(f"Trace Run ID               : {result.trace_id}")
        print(f"Case ID                    : {result.case_id or 'N/A'}")
        print(f"Starting Wallet            : {result.starting_wallet}")
        print(f"Chain / Asset              : {result.chain}")
        print(f"Status                     : {result.status}")
        print(f"Model Version              : {result.scoring_model_version}")
        print(f"Evaluated At               : {result.evaluated_at}")
        print("-" * 80)
        print(f"Analytical Explanation:\n  {result.explanation}")
        print("-" * 80)

        if not result.candidates:
            print("No VASP candidate endpoints detected along the trace graph.")
        else:
            print(f"Ranked VASP Candidate Endpoints ({len(result.candidates)} candidates identified):")
            for c in result.candidates:
                print(f"\n  [Rank #{c.rank}] Candidate: {c.candidate_name}")
                print(f"    - Endpoint Address    : {c.endpoint_address}")
                print(f"    - Hop Distance        : {c.endpoint_hop_distance} hop(s)")
                print(f"    - Attribution Type    : {c.attribution_type}")
                print(f"    - Source Confidence   : {c.source_confidence:.4f} (0.0 - 1.0)")
                print(f"    - VASP Score          : {c.attribution_confidence:.2f} / 100.0")
                print(f"    - Confidence Band     : {c.confidence_band}")
                print(f"    - Source Provenance   : {c.source_metadata.get('source')} (Level {c.source_metadata.get('source_quality_level')})")
                print("    - Score Components:")
                for comp_name, comp_val in c.score_components.items():
                    print(f"        * {comp_name}: {comp_val} pts")
                print("    - Supporting Evidence Statements:")
                for stmt in c.evidence_summary:
                    print(f"        * {stmt}")
                print(f"    - Path Sequence       : {' -> '.join(c.path_sequence)}")
                print(f"    - Supporting Txs      : {len(c.supporting_transactions)} tx hash(es)")

        print("=" * 80 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_vasp_resolution())
