import time
import uuid
import logging
from collections import deque
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.blockchain.base import BlockchainAdapter
from app.blockchain.registry import ChainRegistry
from app.blockchain.tron.adapter import TRON_USDT_CONTRACT
from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.schemas.trace import TraceRequest, TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.transaction import NormalizedTransactionBase

logger = logging.getLogger("specter.tracing")


KNOWN_CONTRACT_ADDRESSES = {
    TRON_USDT_CONTRACT.upper(),
    "TEZFAYL8TEWPCEE9KWSCBRUE65GMMDTBQL",  # Tether Treasury Contract / Issuer
}


class TraceEngine:
    """
    Chain-agnostic Multi-Hop Fund-Tracing Engine.
    Performs priority-guided downstream BFS fund-flow graph traversal,
    cycle detection, path metrics extraction, and Path Relevance scoring.
    """

    def __init__(self, db: Session, adapter: Optional[BlockchainAdapter] = None):
        self.db = db
        self.adapter = adapter

    async def execute_trace(self, request: TraceRequest, case_id: Optional[str] = None) -> TraceResultResponse:
        start_time_monotonic = time.monotonic()
        start_dt = datetime.now(timezone.utc)
        trace_id = str(uuid.uuid4())

        self.adapter = self.adapter or ChainRegistry.get_adapter(request.chain)
        starting_wallet = request.starting_wallet.strip()



        # Create initial TraceRun record
        trace_run = TraceRun(
            trace_id=trace_id,
            case_id=case_id,
            starting_wallet=starting_wallet,
            chain=request.chain.upper(),
            asset=request.asset.upper(),
            max_hops=request.max_hops,
            parameters=request.model_dump(mode="json"),
            status="FETCHING",
            started_at=start_dt,
        )
        self.db.add(trace_run)
        self.db.commit()

        # Global tracing state tracking
        visited_nodes: Dict[str, TraceNode] = {}
        all_edges: List[TraceEdge] = []
        all_paths: List[TracePathDetail] = []

        discovered_wallets: Set[str] = {starting_wallet}
        total_tx_analyzed = 0
        truncated = False
        truncation_reason: Optional[str] = None

        # Add starting node
        start_node = TraceNode(
            trace_id=trace_id,
            wallet_address=starting_wallet,
            hop=0,
            transaction_count=0,
            first_discovered_at=start_dt,
            is_starting_wallet=True,
        )
        self.db.add(start_node)
        visited_nodes[starting_wallet] = start_node

        # Traversal Queue item format:
        # (current_wallet, current_hop, path_addresses_list, path_txs_list)
        queue = deque([(starting_wallet, 0, [starting_wallet], [])])

        while queue:
            # Hard limit checks
            if total_tx_analyzed >= request.max_total_transactions:
                truncated = True
                truncation_reason = f"MAX_TOTAL_TRANSACTIONS hard limit ({request.max_total_transactions}) reached"
                logger.warning(f"Trace {trace_id}: {truncation_reason}")
                break

            if len(all_edges) >= 1000 or len(discovered_wallets) >= 500:
                truncated = True
                truncation_reason = "Hard limit on graph edge/node size reached"
                logger.warning(f"Trace {trace_id}: {truncation_reason}")
                break

            curr_wallet, curr_hop, curr_path_addrs, curr_path_txs = queue.popleft()

            # Skip contract addresses from intermediate hop expansion
            if curr_wallet.upper() in KNOWN_CONTRACT_ADDRESSES and curr_hop > 0:
                logger.info(f"Skipping contract address {curr_wallet} from downstream hop expansion")
                continue

            if curr_hop >= request.max_hops:
                continue

            # Fetch transactions for current wallet
            token_contract = TRON_USDT_CONTRACT if request.asset.upper() == "USDT" else None

            # Determine pages based on max_transactions_per_wallet
            max_pages = max(1, request.max_transactions_per_wallet // 50)

            try:
                if hasattr(self.adapter, "get_all_token_transfers"):
                    fetch_res = await self.adapter.get_all_token_transfers(
                        address=curr_wallet,
                        token_contract=token_contract,
                        max_pages=max_pages,
                        page_size=min(request.max_transactions_per_wallet, 50),
                    )
                    fetched_txs: List[NormalizedTransactionBase] = fetch_res.get("transactions", [])
                else:
                    raw_txs = await self.adapter.get_token_transfers(
                        address=curr_wallet,
                        token_contract=token_contract,
                        limit=min(request.max_transactions_per_wallet, 50),
                    )
                    fetched_txs = [self.adapter.normalize_transaction(raw) for raw in raw_txs]
            except Exception as e:
                logger.error(f"Error fetching transfers for {curr_wallet}: {e}")
                continue


            # Enforce hard transaction ceiling strictly against batch overshoot
            remaining_quota = max(0, request.max_total_transactions - total_tx_analyzed)
            if len(fetched_txs) > remaining_quota:
                fetched_txs = fetched_txs[:remaining_quota]
                truncated = True
                truncation_reason = f"MAX_TOTAL_TRANSACTIONS hard limit ({request.max_total_transactions}) reached"

            total_tx_analyzed += len(fetched_txs)

            # Update wallet node transaction count
            if curr_wallet in visited_nodes:
                visited_nodes[curr_wallet].transaction_count += len(fetched_txs)

            # Persist raw/normalized transactions into main DB table
            self.adapter.persist_transactions(self.db, fetched_txs, case_id=case_id)

            # Filter outgoing transfers from curr_wallet
            outgoing_txs = []
            for tx in fetched_txs:
                if tx.from_address.upper() != curr_wallet.upper():
                    continue  # Ignore incoming or unrelated transfers in outgoing trace
                if tx.to_address.upper() == curr_wallet.upper():
                    continue  # Ignore self-transfers
                if tx.amount < request.min_transfer_amount:
                    continue  # Filter dust below threshold
                if request.asset and tx.asset.upper() != request.asset.upper():
                    continue
                if request.time_window_start and tx.timestamp < request.time_window_start:
                    continue
                if request.time_window_end and tx.timestamp > request.time_window_end:
                    continue

                outgoing_txs.append(tx)

            # Sort outgoing transfers by amount descending (greedy branch expansion)
            outgoing_txs.sort(key=lambda t: t.amount, reverse=True)

            # Limit branch fan-out per node
            branches = outgoing_txs[: request.max_children_per_node]

            for tx in branches:
                recipient = tx.to_address.strip()
                discovered_wallets.add(recipient)

                # Calculate delta_t from previous hop in current path
                delta_t = None
                if curr_path_txs:
                    last_tx = curr_path_txs[-1]
                    delta_t = max(0.0, (tx.timestamp - last_tx.timestamp).total_seconds())

                # Record edge
                edge_model = TraceEdge(
                    trace_id=trace_id,
                    from_wallet=curr_wallet,
                    to_wallet=recipient,
                    tx_hash=tx.tx_hash,
                    amount=tx.amount,
                    asset=tx.asset,
                    timestamp=tx.timestamp,
                    hop=curr_hop + 1,
                    delta_t_seconds=delta_t,
                    explorer_url=tx.explorer_url,
                )
                self.db.add(edge_model)
                all_edges.append(edge_model)

                # Record node if not already present
                if recipient not in visited_nodes:
                    node_model = TraceNode(
                        trace_id=trace_id,
                        wallet_address=recipient,
                        hop=curr_hop + 1,
                        transaction_count=0,
                        first_discovered_at=tx.timestamp,
                        is_starting_wallet=False,
                    )
                    self.db.add(node_model)
                    visited_nodes[recipient] = node_model

                new_path_addrs = curr_path_addrs + [recipient]
                new_path_txs = curr_path_txs + [tx]

                # Cycle Detection
                cycle_detected = recipient.upper() in [a.upper() for a in curr_path_addrs]

                # Evaluate Path
                path_detail = self._build_path_detail(
                    trace_id=trace_id,
                    path_addrs=new_path_addrs,
                    path_txs=new_path_txs,
                    cycle_detected=cycle_detected,
                )
                all_paths.append(path_detail)

                # Only queue next hop if hop limit not reached, no cycle detected, and recipient is not a smart contract
                if not cycle_detected and (curr_hop + 1) < request.max_hops and recipient.upper() not in KNOWN_CONTRACT_ADDRESSES:
                    queue.append((recipient, curr_hop + 1, new_path_addrs, new_path_txs))

        # Sort all paths by relevance score descending
        all_paths.sort(key=lambda p: p.relevance_score, reverse=True)

        # Select top non-redundant paths to return and persist
        persisted_paths = []
        for path in all_paths[:50]:  # Keep top 50 relevant paths
            db_path = TracePath(
                trace_id=trace_id,
                path_id=path.path_id,
                wallet_sequence=path.wallet_sequence,
                edge_sequence=[h.tx_hash for h in path.hops],
                hop_count=path.hop_count,
                initial_amount=path.initial_amount,
                final_amount=path.final_amount,
                value_retention_percent=path.value_retention_percent,
                elapsed_time_seconds=path.elapsed_time_seconds,
                relevance_score=path.relevance_score,
                metrics=path.metrics,
                relevance_explanation=path.relevance_explanation,
                cycle_detected=path.cycle_detected,
            )
            self.db.add(db_path)
            persisted_paths.append(path)

        end_time_monotonic = time.monotonic()
        elapsed_seconds = round(end_time_monotonic - start_time_monotonic, 3)
        completed_dt = datetime.now(timezone.utc)

        # Update TraceRun completion metadata
        trace_run.status = "COMPLETED" if not truncated else "TRUNCATED"
        trace_run.truncated = truncated
        trace_run.truncation_reason = truncation_reason
        trace_run.total_wallets_discovered = len(discovered_wallets)
        trace_run.total_transactions_analyzed = total_tx_analyzed
        trace_run.total_edges_discovered = len(all_edges)
        trace_run.total_paths_found = len(all_paths)
        trace_run.completed_at = completed_dt
        trace_run.processing_time_seconds = elapsed_seconds

        self.db.commit()

        return TraceResultResponse(
            trace_id=trace_id,
            case_id=case_id,
            starting_wallet=starting_wallet,
            chain=request.chain.upper(),
            asset=request.asset.upper(),
            status=trace_run.status,
            truncated=truncated,
            truncation_reason=truncation_reason,
            total_wallets_discovered=len(discovered_wallets),
            total_transactions_analyzed=total_tx_analyzed,
            total_edges_discovered=len(all_edges),
            total_paths_found=len(all_paths),
            processing_time_seconds=elapsed_seconds,
            started_at=start_dt,
            completed_at=completed_dt,
            paths=persisted_paths,
        )

    def _build_path_detail(
        self,
        trace_id: str,
        path_addrs: List[str],
        path_txs: List[NormalizedTransactionBase],
        cycle_detected: bool,
    ) -> TracePathDetail:
        """
        Reconstruct path metrics, calculate exact value retention using Decimal,
        compute time deltas, and evaluate Path Relevance Score.
        """
        hop_count = len(path_txs)
        initial_amount = path_txs[0].amount if path_txs else 0.0
        final_amount = path_txs[-1].amount if path_txs else 0.0

        # Decimal precision for value retention calculation
        if initial_amount > 0:
            retention_dec = (Decimal(str(final_amount)) / Decimal(str(initial_amount))) * Decimal("100.0")
            value_retention_percent = float(min(Decimal("100.0"), max(Decimal("0.0"), retention_dec)))
        else:
            value_retention_percent = 0.0

        # Time metrics & Hop items
        hops: List[TraceHopItem] = []
        delta_ts: List[float] = []

        first_ts = path_txs[0].timestamp
        last_ts = path_txs[-1].timestamp
        elapsed_time_seconds = max(0.0, (last_ts - first_ts).total_seconds())

        for idx, tx in enumerate(path_txs, start=1):
            delta_t = None
            if idx > 1:
                prev_tx = path_txs[idx - 2]
                delta_t = max(0.0, (tx.timestamp - prev_tx.timestamp).total_seconds())
                delta_ts.append(delta_t)

            hops.append(
                TraceHopItem(
                    hop_number=idx,
                    from_address=tx.from_address,
                    to_address=tx.to_address,
                    tx_hash=tx.tx_hash,
                    asset=tx.asset,
                    amount=tx.amount,
                    timestamp=tx.timestamp,
                    block_number=tx.block_number,
                    delta_t_seconds=delta_t,
                    explorer_url=tx.explorer_url,
                )
            )

        avg_delta = float(sum(delta_ts) / len(delta_ts)) if delta_ts else 0.0
        min_delta = float(min(delta_ts)) if delta_ts else 0.0
        max_delta = float(max(delta_ts)) if delta_ts else 0.0

        metrics = {
            "avg_delta_t_seconds": round(avg_delta, 1),
            "min_delta_t_seconds": round(min_delta, 1),
            "max_delta_t_seconds": round(max_delta, 1),
            "unique_wallets": len(set(path_addrs)),
            "tx_count": len(path_txs),
        }

        # Calculate Path Relevance Score (0 - 100)
        relevance_score, explanations = self._calculate_relevance_score(
            initial_amount=initial_amount,
            final_amount=final_amount,
            value_retention=value_retention_percent,
            hop_count=hop_count,
            avg_delta_t=avg_delta,
            cycle_detected=cycle_detected,
        )

        path_id = f"path_{uuid.uuid4().hex[:12]}"

        return TracePathDetail(
            path_id=path_id,
            wallet_sequence=path_addrs,
            hop_count=hop_count,
            initial_amount=initial_amount,
            final_amount=final_amount,
            value_retention_percent=round(value_retention_percent, 2),
            elapsed_time_seconds=round(elapsed_time_seconds, 1),
            relevance_score=round(relevance_score, 1),
            relevance_explanation=explanations,
            cycle_detected=cycle_detected,
            metrics=metrics,
            hops=hops,
        )

    def _calculate_relevance_score(
        self,
        initial_amount: float,
        final_amount: float,
        value_retention: float,
        hop_count: int,
        avg_delta_t: float,
        cycle_detected: bool,
    ) -> Tuple[float, List[str]]:
        """
        Calculate explainable Path Relevance Score (0 - 100).
        Component weights:
        - Value Continuity (40 pts)
        - Temporal Continuity (30 pts)
        - Value Magnitude (20 pts)
        - Path Length / Directness (10 pts)
        """
        explanations = []

        # 1. Value Continuity Score (40 pts max)
        val_ratio = min(1.0, value_retention / 100.0) if value_retention > 0 else 0.0
        val_score = val_ratio * 40.0
        explanations.append(f"{round(value_retention, 1)}% value retention (+{round(val_score, 1)} pts)")

        # 2. Temporal Continuity Score (30 pts max)
        if avg_delta_t < 300:  # < 5 mins
            temp_score = 30.0
            explanations.append(f"Rapid velocity: avg delta_t {round(avg_delta_t, 1)}s < 5m (+30.0 pts)")
        elif avg_delta_t < 3600:  # < 1 hr
            temp_score = 25.0
            explanations.append(f"High temporal continuity: avg delta_t {round(avg_delta_t/60, 1)}m (+25.0 pts)")
        elif avg_delta_t < 86400:  # < 24 hrs
            temp_score = 18.0
            explanations.append(f"Moderate temporal continuity: avg delta_t {round(avg_delta_t/3600, 1)}h (+18.0 pts)")
        elif avg_delta_t < 604800:  # < 7 days
            temp_score = 10.0
            explanations.append(f"Fair temporal continuity (+10.0 pts)")
        else:
            temp_score = 5.0
            explanations.append(f"Delayed temporal gap (+5.0 pts)")

        # 3. Value Magnitude Score (20 pts max)
        if final_amount >= 10000.0:
            mag_score = 20.0
            explanations.append(f"Significant transfer magnitude: {final_amount:,.2f} USDT (+20.0 pts)")
        elif final_amount >= 1000.0:
            mag_score = 15.0
            explanations.append(f"Moderate transfer magnitude: {final_amount:,.2f} USDT (+15.0 pts)")
        elif final_amount >= 100.0:
            mag_score = 10.0
            explanations.append(f"Standard transfer magnitude (+10.0 pts)")
        else:
            mag_score = 5.0
            explanations.append(f"Low transfer magnitude (+5.0 pts)")

        # 4. Path Length Score (10 pts max)
        if 1 <= hop_count <= 3:
            path_score = 10.0
            explanations.append(f"Direct flow: {hop_count} hops (+10.0 pts)")
        elif hop_count <= 5:
            path_score = 7.0
            explanations.append(f"Multi-hop flow: {hop_count} hops (+7.0 pts)")
        else:
            path_score = 4.0
            explanations.append(f"Extended multi-hop flow (+4.0 pts)")

        total_score = val_score + temp_score + mag_score + path_score

        if cycle_detected:
            total_score *= 0.8  # 20% penalty for circular transfers
            explanations.append("Cycle detected in path (-20% penalty applied)")

        final_score = min(100.0, max(0.0, total_score))
        return final_score, explanations
