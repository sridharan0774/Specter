import sys
import os
import argparse
import asyncio
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.blockchain.tron import TronAdapter, TRON_USDT_CONTRACT


async def run_smoke_test(address: str, limit: int, asset: str, pages: int):
    print("==================================================")
    print(" SPECTER REAL-DATA TRON SMOKE TEST")
    print("==================================================")
    print(f"Target Address : {address}")
    print(f"Target Asset   : {asset}")
    print(f"Max Pages      : {pages}")
    print(f"Page Limit     : {limit}")
    print("--------------------------------------------------")

    adapter = TronAdapter()

    # 1. Address Validation
    is_valid = adapter.validate_address(address)
    print(f"[1] Address Validation Check : {'VALID' if is_valid else 'INVALID'}")
    if not is_valid:
        print(f"ERROR: Address '{address}' is not a valid TRON base58 address.")
        sys.exit(1)

    # 2. Database Initialization
    init_db()
    db = SessionLocal()

    # 3. Live API Fetching & Pagination
    print("\n[2] Connecting to public TronGrid API for real data ingestion...")
    token_contract = TRON_USDT_CONTRACT if asset.upper() == "USDT" else None
    
    result = await adapter.get_all_token_transfers(
        address=address,
        token_contract=token_contract,
        max_pages=pages,
        page_size=limit
    )

    print("\n[3] Retrieval Summary & Metadata:")
    print(f"    - Provider         : {result['provider']}")
    print(f"    - Status           : {result['status']}")
    print(f"    - Pages Fetched    : {result['pages_fetched']}")
    print(f"    - Records Fetched  : {result['records_fetched']}")
    print(f"    - Retrieval Time   : {result['retrieved_at']}")

    normalized_txs = result["transactions"]
    if not normalized_txs:
        print("\n[!] No transaction records found for the given parameters.")
        db.close()
        return

    # 4. Database Persistence & Deduplication
    print("\n[4] Persisting normalized records into database with deduplication...")
    persisted = adapter.persist_transactions(db=db, transactions=normalized_txs)
    print(f"    - Successfully persisted/verified {len(persisted)} records in SQL database.")

    # 5. Display Sample Real Transactions
    print("\n[5] Sample Normalized Real Transactions (Showing up to 3):")
    for idx, tx in enumerate(normalized_txs[:3], start=1):
        print(f"\n--- Transaction #{idx} ---")
        print(f"  Tx Hash       : {tx.tx_hash}")
        print(f"  Block Number  : {tx.block_number}")
        print(f"  Timestamp     : {tx.timestamp} (UTC)")
        print(f"  From Address  : {tx.from_address}")
        print(f"  To Address    : {tx.to_address}")
        print(f"  Asset         : {tx.asset}")
        print(f"  Amount        : {tx.amount:,.6f}")
        print(f"  Token Contract: {tx.token_contract}")
        print(f"  Explorer URL  : {tx.explorer_url}")

    print("\n==================================================")
    print(" SMOKE TEST SUCCESSFUL: REAL TRON DATA VERIFIED ")
    print("==================================================")
    db.close()


def main():
    parser = argparse.ArgumentParser(description="SPECTER Real-Data TRON Ingestion Smoke Test")
    parser.add_argument(
        "--address",
        type=str,
        default="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        help="REAL TRON wallet or contract address to query (Default: USDT Contract)",
    )
    parser.add_argument("--limit", type=int, default=5, help="Number of records per page (Default: 5)")
    parser.add_argument("--asset", type=str, default="USDT", help="Asset filter: USDT or TRX (Default: USDT)")
    parser.add_argument("--pages", type=int, default=2, help="Max pages to fetch (Default: 2)")

    args = parser.parse_args()
    asyncio.run(run_smoke_test(address=args.address, limit=args.limit, asset=args.asset, pages=args.pages))


if __name__ == "__main__":
    main()
