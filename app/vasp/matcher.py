import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.schemas.trace import TraceResultResponse, TracePathDetail
from app.models.vasp import VASPRecord
from app.vasp.repository import VASPRepository

logger = logging.getLogger("specter.vasp.matcher")


# Standard TRON USDT Contract Address - strictly barred from VASP attribution
TRON_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


class MatchedCandidate:
    """Internal container for an identified VASP candidate endpoint before scoring."""

    def __init__(
        self,
        candidate_name: str,
        matching_address: str,
        chain: str,
        hop_distance: int,
        attribution_type: str,
        vasp_record: Optional[VASPRecord],
        paths_involved: List[TracePathDetail],
        supporting_transactions: List[str],
        supporting_wallets: List[str],
        path_sequence: List[str],
        is_terminal_endpoint: bool = False,
        entity_role: str = "VASP",
        match_position: str = "TERMINAL_ENDPOINT",
        value_transferred: float = 0.0,
        value_retention_percent: float = 0.0,
        temporal_proximity_seconds: float = 0.0,
        path_convergence_count: int = 1,
        incoming_tx_amounts: Optional[Dict[str, float]] = None,
    ):
        self.candidate_name = candidate_name
        self.matching_address = matching_address
        self.chain = chain
        self.hop_distance = hop_distance
        self.attribution_type = attribution_type
        self.vasp_record = vasp_record
        self.paths_involved = paths_involved
        self.supporting_transactions = supporting_transactions
        self.supporting_wallets = supporting_wallets
        self.path_sequence = path_sequence
        self.is_terminal_endpoint = is_terminal_endpoint
        self.entity_role = entity_role
        self.match_position = match_position
        self.value_transferred = value_transferred
        self.value_retention_percent = value_retention_percent
        self.temporal_proximity_seconds = temporal_proximity_seconds
        self.path_convergence_count = path_convergence_count
        self.incoming_tx_amounts = incoming_tx_amounts or {}


class VASPMatcher:
    """
    Analyzes multi-hop trace fund flow graphs to discover potential VASP candidate endpoints.
    Strictly distinguishes between actual VASP endpoints, intermediate path associations,
    and excludes non-VASP entities (e.g. token contracts, token issuers, bridges).
    """

    def __init__(self, repository: VASPRepository):
        self.repository = repository

    def find_candidates(
        self,
        trace_result: TraceResultResponse,
        starting_wallet: str,
    ) -> List[MatchedCandidate]:
        """
        Scan all paths and nodes in a TraceResultResponse to find potential VASP candidates.
        Returns a list of MatchedCandidate objects representing identified candidate endpoints.
        """
        candidates_map: Dict[str, MatchedCandidate] = {}
        starting_wallet_clean = starting_wallet.strip().upper()

        if not trace_result.paths:
            logger.info(f"No paths found in trace {trace_result.trace_id} for VASP matching.")
            return []

        for path in trace_result.paths:
            wallet_seq = path.wallet_sequence
            if not wallet_seq:
                continue

            terminal_wallet = wallet_seq[-1]

            # Collect transaction hashes & intermediate wallets along path
            path_tx_hashes = [h.tx_hash for h in path.hops if h.tx_hash]
            path_wallets = wallet_seq[1:-1] if len(wallet_seq) > 2 else []

            # Check each address along path
            for index, addr in enumerate(wallet_seq):
                if index == 0 and addr.upper() == starting_wallet_clean:
                    # Skip starting wallet itself unless explicitly testing starting wallet
                    continue

                clean_addr = addr.strip()
                clean_addr_upper = clean_addr.upper()

                # CRITICAL: Token contracts must NEVER be treated as VASP candidates
                if clean_addr_upper == TRON_USDT_CONTRACT.upper():
                    logger.debug(f"Skipping USDT token contract address {clean_addr} from VASP matching.")
                    continue

                vasp_record = self.repository.search_entity(clean_addr, trace_result.chain)
                if not vasp_record:
                    continue

                # Enforce entity role: Must be an attributable VASP (not token contract, issuer, or infra)
                if hasattr(vasp_record, "is_attributable_vasp") and not vasp_record.is_attributable_vasp:
                    logger.debug(f"Skipping non-attributable entity {vasp_record.entity_name} ({vasp_record.entity_type}).")
                    continue

                role = (getattr(vasp_record, "entity_role", "VASP") or "VASP").upper()
                etype = (getattr(vasp_record, "entity_type", "") or "").upper()
                if role in ("TOKEN_CONTRACT", "TOKEN_ISSUER", "INFRASTRUCTURE") or etype in ("TOKEN_CONTRACT", "TOKEN_ISSUER", "INFRASTRUCTURE"):
                    continue

                # Distinguish terminal endpoint from intermediate association
                is_terminal_for_this_path = (clean_addr_upper == terminal_wallet.strip().upper())
                hop_dist = index

                # Determine attribution classification based on entity label & path location
                attribution_type = self._classify_attribution_type(
                    vasp_record=vasp_record,
                    is_terminal=is_terminal_for_this_path,
                    hop_distance=hop_dist,
                )
                match_pos = "TERMINAL_ENDPOINT" if is_terminal_for_this_path else "INTERMEDIATE_ASSOCIATION"

                # Collect strictly relevant transaction hashes & intermediate wallets leading up to this hop
                leading_hops = path.hops[:index] if (path.hops and len(path.hops) >= index) else []
                leading_tx_hashes = [h.tx_hash for h in leading_hops if h.tx_hash]
                leading_wallets = [w for w in wallet_seq[:index] if w.upper() != clean_addr_upper and w.upper() != starting_wallet_clean]

                # Identify the specific incoming hop transaction that transferred funds into clean_addr
                incoming_hop = leading_hops[-1] if leading_hops else None
                incoming_tx_hash = incoming_hop.tx_hash if incoming_hop else (leading_tx_hashes[-1] if leading_tx_hashes else None)

                # Calculate path metrics up to this hop
                transfer_val = path.final_amount if is_terminal_for_this_path else path.initial_amount
                if incoming_hop and incoming_hop.amount is not None:
                    transfer_val = incoming_hop.amount

                val_retention = path.value_retention_percent if is_terminal_for_this_path else (
                    (transfer_val / path.initial_amount * 100.0) if path.initial_amount > 0 else 50.0
                )
                elapsed_sec = path.elapsed_time_seconds

                key = f"{vasp_record.entity_name}:{clean_addr}"
                incoming_amounts = {incoming_tx_hash: transfer_val} if incoming_tx_hash else {}

                if key not in candidates_map:
                    candidates_map[key] = MatchedCandidate(
                        candidate_name=vasp_record.entity_name,
                        matching_address=clean_addr,
                        chain=trace_result.chain,
                        hop_distance=hop_dist,
                        attribution_type=attribution_type,
                        vasp_record=vasp_record,
                        paths_involved=[path],
                        supporting_transactions=list(leading_tx_hashes),
                        supporting_wallets=list(leading_wallets),
                        path_sequence=list(wallet_seq[: index + 1]),
                        is_terminal_endpoint=is_terminal_for_this_path,
                        entity_role=getattr(vasp_record, "entity_role", "VASP") or "VASP",
                        match_position=match_pos,
                        value_transferred=transfer_val,
                        value_retention_percent=val_retention,
                        temporal_proximity_seconds=elapsed_sec,
                        path_convergence_count=1,
                        incoming_tx_amounts=incoming_amounts,
                    )
                else:
                    existing = candidates_map[key]
                    # If any path terminates at this entity, it is a terminal endpoint for that flow
                    if is_terminal_for_this_path:
                        existing.is_terminal_endpoint = True
                        existing.match_position = "TERMINAL_ENDPOINT"
                        existing.attribution_type = self._classify_attribution_type(
                            vasp_record=vasp_record,
                            is_terminal=True,
                            hop_distance=min(existing.hop_distance, hop_dist),
                        )

                    # Update shortest hop distance and path sequence
                    if hop_dist < existing.hop_distance:
                        existing.hop_distance = hop_dist
                        existing.path_sequence = list(wallet_seq[: index + 1])

                    # Deduplicate paths by path_id so duplicate subpaths or cycles are never double-counted
                    if path.path_id not in [p.path_id for p in existing.paths_involved]:
                        existing.paths_involved.append(path)
                    existing.path_convergence_count = len(existing.paths_involved)

                    # Aggregate value transferred without double-counting incoming transactions
                    if incoming_tx_hash:
                        existing.incoming_tx_amounts[incoming_tx_hash] = transfer_val
                        existing.value_transferred = round(sum(existing.incoming_tx_amounts.values()), 6)
                    else:
                        existing.value_transferred = max(existing.value_transferred, transfer_val)

                    existing.value_retention_percent = max(existing.value_retention_percent, val_retention)
                    existing.temporal_proximity_seconds = min(existing.temporal_proximity_seconds, elapsed_sec)

                    for tx in leading_tx_hashes:
                        if tx not in existing.supporting_transactions:
                            existing.supporting_transactions.append(tx)
                    for w in leading_wallets:
                        if w not in existing.supporting_wallets and w != clean_addr:
                            existing.supporting_wallets.append(w)

        return list(candidates_map.values())

    def _classify_attribution_type(
        self,
        vasp_record: VASPRecord,
        is_terminal: bool,
        hop_distance: int,
    ) -> str:
        """
        Classifies the relationship between the candidate address and the VASP entity.
        Strictly distinguishes DIRECT / TERMINAL ENDPOINTS from INTERMEDIATE ASSOCIATIONS.
        Rules:
        - Terminal endpoint matching known deposit wallet -> KNOWN_DEPOSIT_ENDPOINT
        - Terminal endpoint matching known hot wallet -> KNOWN_HOT_WALLET
        - Terminal endpoint matching custodial wallet -> KNOWN_CUSTODIAL_WALLET
        - Terminal endpoint matching other registered VASP address -> EXACT_ENDPOINT_MATCH
        - Intermediate hop with VASP label -> INTERMEDIATE_ASSOCIATION (never treated as endpoint)
        """
        label = (vasp_record.label_type or "").lower()
        entity_type = (vasp_record.entity_type or "").upper()

        if is_terminal:
            if "deposit" in label or "deposit" in entity_type.lower():
                return "KNOWN_DEPOSIT_ENDPOINT"
            elif "hot" in label or "hot" in entity_type.lower():
                return "KNOWN_HOT_WALLET"
            elif "cold" in label or "cold" in entity_type.lower():
                return "KNOWN_COLD_WALLET"
            elif "custodial" in label or "custodial" in entity_type.lower():
                return "KNOWN_CUSTODIAL_WALLET"
            else:
                return "EXACT_ENDPOINT_MATCH"
        else:
            return "INTERMEDIATE_ASSOCIATION"
