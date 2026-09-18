import sys
import asyncio
import argparse
from datetime import datetime, timezone

from app.core.database import SessionLocal, init_db
from app.schemas.trace import TraceRequest
from app.tracing.engine import TraceEngine
from app.blockchain.tron.adapter import TronAdapter

# High-activity known TRON address for live testing
DEFAULT_TRON_TARGET = "TMuA6YXYTBwyAKBGD2FJhchHjK45L1Gvh4"


async def main():
    parser = argparse.ArgumentParser(description="SPECTER Real-Data Multi-Hop TRON USDT Trace Engine CLI")
    parser.add_argument("--address", type=str, default=DEFAULT_TRON_TARGET, help="Starting TRON wallet address")
    parser.add_argument("--hops", type=int, default=3, help="Maximum hop depth (default: 3)")
    parser.add_argument("--min-amount", type=float, default=10.0, help="Minimum USDT transfer threshold to trace")
    parser.add_argument("--max-tx", type=int, default=30, help="Max transactions to examine per wallet")
    parser.add_argument("--max-total-tx", type=int, default=200, help="Hard cap on total transactions examined")
    parser.add_argument("--case-id", type=str, default=None, help="Optional case ID to associate with trace")

    args = parser.parse_args()

    print("=" * 80)
    print(" SPECTER AUTOMATED BLOCKCHAIN INTELLIGENCE ENGINE ")
    print(" Real-Data Multi-Hop Fund-Tracing Module ")
    print("=" * 80)
    print(f" Target Starting Wallet : {args.address}")
    print(f" Chain / Asset          : TRON / USDT")
    print(f" Max Depth (Hops)       : {args.hops}")
    print(f" Minimum Transfer Threshold: {args.min_amount} USDT")
    print(f" Started At             : {datetime.now(timezone.utc).isoformat()}")
    print("-" * 80)

    # Initialize DB schema
    init_db()
    db = SessionLocal()

    try:
        adapter = TronAdapter()
        engine = TraceEngine(db=db, adapter=adapter)

        request = TraceRequest(
            starting_wallet=args.address,
            chain="TRON",
            asset="USDT",
            max_hops=args.hops,
            min_transfer_amount=args.min_amount,
            max_transactions_per_wallet=args.max_tx,
            max_total_transactions=args.max_total_tx,
            max_children_per_node=5,
        )

        print("[*] Initiating priority BFS graph traversal on TRON blockchain...")
        result = await engine.execute_trace(request=request, case_id=args.case_id)

        print("\n" + "=" * 80)
        print(" TRACE RESULT SUMMARY ")
        print("=" * 80)
        print(f" Trace ID                 : {result.trace_id}")
        print(f" Status                   : {result.status}")
        print(f" Truncated                : {result.truncated} ({result.truncation_reason or 'None'})")
        print(f" Total Discovered Wallets : {result.total_wallets_discovered}")
        print(f" Total Transactions Examined: {result.total_transactions_analyzed}")
        print(f" Total Graph Edges        : {result.total_edges_discovered}")
        print(f" Total Paths Found        : {result.total_paths_found}")
        print(f" Execution Time           : {result.processing_time_seconds:.3f} seconds")
        print("-" * 80)

        if not result.paths:
            print("[!] No outgoing paths meeting the criteria were found.")
            return

        print(f"\n[+] Displaying Top {min(5, len(result.paths))} Reconstructed Paths (Ranked by Relevance Score):\n")
        
        for idx, path in enumerate(result.paths[:5], start=1):
            print(f"--------------------------------------------------------------------------------")
            print(f" Path #{idx} | Path ID: {path.path_id}")
            print(f" Relevance Score: {path.relevance_score}/100 | Cycle Detected: {path.cycle_detected}")
            print(f" Hops: {path.hop_count} | Value Retention: {path.value_retention_percent}% ({path.initial_amount:,.2f} -> {path.final_amount:,.2f} USDT)")
            print(f" Elapsed Flow Time: {path.elapsed_time_seconds:.1f} seconds")
            print(" Explanations:")
            for exp in path.relevance_explanation:
                print(f"   • {exp}")
            
            print("\n Hop Details:")
            for hop in path.hops:
                delta_str = f"{hop.delta_t_seconds:.1f}s" if hop.delta_t_seconds is not None else "N/A (Origin)"
                block_str = str(hop.block_number) if hop.block_number is not None else "NULL"
                print(f"   Hop {hop.hop_number}: {hop.from_address[:12]}... -> {hop.to_address[:12]}...")
                print(f"          Amount: {hop.amount:,.2f} USDT | Block: {block_str} | Delta-T: {delta_str}")
                print(f"          Tx Hash: {hop.tx_hash}")
                print(f"          Explorer: {hop.explorer_url}")
            print()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
