import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TraceNode, TraceEdge, TracePath
from app.schemas.trace import TraceResultResponse, TracePathDetail
from app.models.vasp import VASPRecord
from app.vasp.repository import VASPRepository

logger = logging.getLogger("specter.vasp.matcher")


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


class VASPMatcher:
    """
    Analyzes multi-hop trace fund flow graphs to discover potential VASP candidate endpoints.
    Distinguishes between exact terminal endpoints, deposit wallets, hot wallets, and intermediate hops.
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
                vasp_record = self.repository.search_entity(clean_addr, trace_result.chain)

                if vasp_record:
                    is_terminal = (clean_addr.upper() == terminal_wallet.strip().upper())
                    hop_dist = index

                    # Determine attribution classification based on entity label & path location
                    attribution_type = self._classify_attribution_type(
                        vasp_record=vasp_record,
                        is_terminal=is_terminal,
                        hop_distance=hop_dist,
                    )

                    key = f"{vasp_record.entity_name}:{clean_addr}"
                    if key not in candidates_map:
                        candidates_map[key] = MatchedCandidate(
                            candidate_name=vasp_record.entity_name,
                            matching_address=clean_addr,
                            chain=trace_result.chain,
                            hop_distance=hop_dist,
                            attribution_type=attribution_type,
                            vasp_record=vasp_record,
                            paths_involved=[path],
                            supporting_transactions=list(path_tx_hashes),
                            supporting_wallets=list(path_wallets),
                            path_sequence=list(wallet_seq[: index + 1]),
                            is_terminal_endpoint=is_terminal,
                        )
                    else:
                        # Merge paths and update hop distance to shortest found
                        existing = candidates_map[key]
                        if hop_dist < existing.hop_distance:
                            existing.hop_distance = hop_dist
                            existing.path_sequence = list(wallet_seq[: index + 1])
                        
                        existing.paths_involved.append(path)
                        for tx in path_tx_hashes:
                            if tx not in existing.supporting_transactions:
                                existing.supporting_transactions.append(tx)
                        for w in path_wallets:
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
        Rules:
        - Exact terminal endpoint matching known address -> EXACT_ENDPOINT_MATCH or KNOWN_DEPOSIT_ENDPOINT
        - Labeled as deposit_wallet -> KNOWN_DEPOSIT_ENDPOINT
        - Labeled as hot_wallet -> KNOWN_HOT_WALLET
        - Labeled as custodial_wallet -> KNOWN_CUSTODIAL_WALLET
        - Intermediate hop with VASP label -> INDIRECT_ASSOCIATION
        """
        label = (vasp_record.label_type or "").lower()
        entity_type = (vasp_record.entity_type or "").upper()

        if is_terminal:
            if "deposit" in label or "deposit" in entity_type.lower():
                return "KNOWN_DEPOSIT_ENDPOINT"
            elif "hot" in label or "hot" in entity_type.lower():
                return "KNOWN_HOT_WALLET"
            elif "custodial" in label or "custodial" in entity_type.lower():
                return "KNOWN_CUSTODIAL_WALLET"
            else:
                return "EXACT_ENDPOINT_MATCH"
        else:
            if "deposit" in label:
                return "KNOWN_DEPOSIT_ENDPOINT"
            elif "hot" in label:
                return "KNOWN_HOT_WALLET"
            else:
                return "INDIRECT_ASSOCIATION"
