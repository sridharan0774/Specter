import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone

from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.velocity import RollingWindowMetric

logger = logging.getLogger("specter.velocity.detector")

DEFAULT_ROLLING_WINDOWS = {
    "1m": 60,
    "5m": 300,
    "10m": 600,
    "30m": 1800,
    "1h": 3600,
}


class VelocityMetrics:
    """Internal container holding raw computed velocity metrics for a graph or path set."""

    def __init__(
        self,
        transfer_count: int,
        total_amount: float,
        duration_seconds: float,
        minimum_delta_t: Optional[float],
        average_delta_t: Optional[float],
        maximum_delta_t: Optional[float],
        unique_recipients: int,
        downstream_hops: int,
        supporting_transactions: List[str],
        supporting_wallets: List[str],
        rolling_windows: Dict[str, RollingWindowMetric],
        delta_ts: List[float],
        initial_transfer_amount: float = 0.0,
        downstream_activity_amount: float = 0.0,
    ):
        self.transfer_count = transfer_count
        self.total_amount = total_amount
        self.duration_seconds = duration_seconds
        self.minimum_delta_t = minimum_delta_t
        self.average_delta_t = average_delta_t
        self.maximum_delta_t = maximum_delta_t
        self.unique_recipients = unique_recipients
        self.downstream_hops = downstream_hops
        self.supporting_transactions = supporting_transactions
        self.supporting_wallets = supporting_wallets
        self.rolling_windows = rolling_windows
        self.delta_ts = delta_ts
        self.initial_transfer_amount = initial_transfer_amount
        self.downstream_activity_amount = downstream_activity_amount


class VelocityDetector:
    """
    Analyzes fund-flow graph transactions to compute delta_t gaps, velocity,
    rolling time window metrics, and downstream path traversal statistics.
    """

    def analyze_trace_velocity(self, trace_result: TraceResultResponse) -> VelocityMetrics:
        """Extract velocity metrics across all paths and hops in a TraceResultResponse."""
        all_hops: List[TraceHopItem] = []
        for path in trace_result.paths:
            for hop in path.hops:
                all_hops.append(hop)

        # Deduplicate hops by tx_hash
        unique_hops_map: Dict[str, TraceHopItem] = {}
        for h in all_hops:
            if h.tx_hash and h.tx_hash not in unique_hops_map:
                unique_hops_map[h.tx_hash] = h

        unique_hops = list(unique_hops_map.values())
        unique_hops.sort(key=lambda x: x.timestamp)

        transfer_count = len(unique_hops)
        if transfer_count == 0:
            return VelocityMetrics(
                transfer_count=0,
                total_amount=0.0,
                duration_seconds=0.0,
                minimum_delta_t=None,
                average_delta_t=None,
                maximum_delta_t=None,
                unique_recipients=0,
                downstream_hops=0,
                supporting_transactions=[],
                supporting_wallets=[],
                rolling_windows=self._empty_rolling_windows(),
                delta_ts=[],
                initial_transfer_amount=0.0,
                downstream_activity_amount=0.0,
            )

        total_amount = sum(h.amount for h in unique_hops)
        tx_hashes = [h.tx_hash for h in unique_hops]

        recipients_set: Set[str] = {h.to_address for h in unique_hops}
        wallets_set: Set[str] = set()
        for h in unique_hops:
            wallets_set.add(h.from_address)
            wallets_set.add(h.to_address)

        # Separate initial transfers from starting wallet from downstream activity
        starting_wallet_clean = (trace_result.starting_wallet or "").strip().upper()
        initial_hops = [h for h in unique_hops if h.from_address.strip().upper() == starting_wallet_clean]
        downstream_hops_list = [h for h in unique_hops if h.from_address.strip().upper() != starting_wallet_clean]

        if initial_hops:
            initial_transfer_amount = sum(h.amount for h in initial_hops)
            downstream_activity_amount = sum(h.amount for h in downstream_hops_list)
        else:
            initial_transfer_amount = unique_hops[0].amount
            downstream_activity_amount = sum(h.amount for h in unique_hops[1:]) if len(unique_hops) > 1 else 0.0

        # Calculate time gaps (delta_t) only across sequential transfers (>= 2 transfers)
        delta_ts: List[float] = []
        if len(unique_hops) >= 2:
            for i in range(1, len(unique_hops)):
                gap = (unique_hops[i].timestamp - unique_hops[i - 1].timestamp).total_seconds()
                delta_ts.append(max(0.0, gap))

            start_ts = unique_hops[0].timestamp
            end_ts = unique_hops[-1].timestamp
            duration_seconds = max(0.0, (end_ts - start_ts).total_seconds())

            min_delta = round(min(delta_ts), 2) if delta_ts else None
            max_delta = round(max(delta_ts), 2) if delta_ts else None
            avg_delta = round(sum(delta_ts) / len(delta_ts), 2) if delta_ts else None
        else:
            duration_seconds = 0.0
            min_delta = None
            max_delta = None
            avg_delta = None

        max_hops = max([p.hop_count for p in trace_result.paths], default=0)

        # Calculate rolling time windows
        rolling_windows = self.calculate_rolling_windows(unique_hops)

        return VelocityMetrics(
            transfer_count=transfer_count,
            total_amount=round(total_amount, 2),
            duration_seconds=round(duration_seconds, 2),
            minimum_delta_t=min_delta,
            average_delta_t=avg_delta,
            maximum_delta_t=max_delta,
            unique_recipients=len(recipients_set),
            downstream_hops=max_hops,
            supporting_transactions=tx_hashes,
            supporting_wallets=list(wallets_set),
            rolling_windows=rolling_windows,
            delta_ts=delta_ts,
            initial_transfer_amount=round(initial_transfer_amount, 2),
            downstream_activity_amount=round(downstream_activity_amount, 2),
        )

    def calculate_rolling_windows(
        self, hops: List[TraceHopItem]
    ) -> Dict[str, RollingWindowMetric]:
        """Compute metrics for rolling time windows (1m, 5m, 10m, 30m, 1h)."""
        res: Dict[str, RollingWindowMetric] = {}
        if not hops:
            return self._empty_rolling_windows()

        sorted_hops = sorted(hops, key=lambda x: x.timestamp)
        latest_ts = sorted_hops[-1].timestamp

        for name, window_sec in DEFAULT_ROLLING_WINDOWS.items():
            window_hops = [
                h for h in sorted_hops if (latest_ts - h.timestamp).total_seconds() <= window_sec
            ]
            count = len(window_hops)
            tot_amt = sum(h.amount for h in window_hops)
            recipients = len({h.to_address for h in window_hops})

            res[name] = RollingWindowMetric(
                window_name=name,
                window_seconds=window_sec,
                transfer_count=count,
                total_amount=round(tot_amt, 2),
                unique_recipients=recipients,
            )

        return res

    def _empty_rolling_windows(self) -> Dict[str, RollingWindowMetric]:
        return {
            name: RollingWindowMetric(
                window_name=name,
                window_seconds=sec,
                transfer_count=0,
                total_amount=0.0,
                unique_recipients=0,
            )
            for name, sec in DEFAULT_ROLLING_WINDOWS.items()
        }
