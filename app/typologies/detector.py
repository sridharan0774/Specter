import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from app.schemas.trace import TraceResultResponse, TracePathDetail, TraceHopItem
from app.schemas.typology import TypologyResult
from app.vasp.service import VASPService
from sqlalchemy.orm import Session

logger = logging.getLogger("specter.typologies.detector")


class TypologyDetector:
    """
    Rule-based transaction typology engine detecting structural patterns:
    - FAN_OUT (1 -> N distribution)
    - FAN_IN (N -> 1 aggregation)
    - CONSOLIDATION (downstream graph branch convergence)
    - RAPID_PEEL_LIKE_MOVEMENT (sequential layered transfer with short time gaps)
    - REPEATED_INTERACTION (frequent transfer pairs)
    - VASP_CONVERGENCE (multiple paths converging to same VASP endpoint)
    - KNOWN_SERVICE_ENTITY (false-positive safety tag)
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.vasp_service = VASPService(db) if db else None

    def analyze_typologies(self, trace_result: TraceResultResponse) -> List[TypologyResult]:
        """Detect all applicable transaction typologies across the trace graph."""
        results: List[TypologyResult] = []

        if not trace_result.paths:
            return results

        # Flatten all trace hop items
        all_hops: List[TraceHopItem] = []
        for path in trace_result.paths:
            for hop in path.hops:
                all_hops.append(hop)

        # Deduplicate hops by tx_hash
        unique_hops_map: Dict[str, TraceHopItem] = {}
        for h in all_hops:
            if h.tx_hash and h.tx_hash not in unique_hops_map:
                unique_hops_map[h.tx_hash] = h
        hops = list(unique_hops_map.values())

        # Check known VASP entity context for false-positive safety
        vasp_attribution = None
        if self.vasp_service:
            try:
                vasp_attribution = self.vasp_service.resolve_from_trace_result(trace_result)
            except Exception as e:
                logger.warning(f"VASP attribution lookup failed during typology analysis: {e}")

        is_known_service_starting = False
        is_known_service_endpoint = False

        if vasp_attribution and vasp_attribution.candidates:
            is_known_service_endpoint = True
            top_candidate = vasp_attribution.candidates[0]

            # Add KNOWN_SERVICE_ENTITY detection result
            results.append(
                TypologyResult(
                    typology_id=f"typ-service-{trace_result.trace_id[:8]}",
                    typology_name="KNOWN_SERVICE_ENTITY",
                    severity="LOW",
                    description=f"Trace path terminates at or involves known verified service endpoint '{top_candidate.candidate_name}' ({top_candidate.endpoint_address}).",
                    trigger_conditions=["Endpoint matched verified VASP/Exchange database record"],
                    metrics={
                        "candidate_name": top_candidate.candidate_name,
                        "endpoint_address": top_candidate.endpoint_address,
                        "attribution_type": top_candidate.attribution_type,
                        "source_confidence": top_candidate.source_confidence,
                    },
                    supporting_transactions=top_candidate.supporting_transactions,
                    supporting_wallets=[top_candidate.endpoint_address],
                    supporting_paths=top_candidate.path_sequence,
                    confidence=top_candidate.source_confidence,
                    is_known_service=True,
                )
            )

        # 1. FAN_OUT Detection
        fan_out_res = self._detect_fan_out(hops, is_known_service_endpoint)
        if fan_out_res:
            results.append(fan_out_res)

        # 2. FAN_IN Detection
        fan_in_res = self._detect_fan_in(hops, is_known_service_endpoint)
        if fan_in_res:
            results.append(fan_in_res)

        # 3. CONSOLIDATION Detection
        consolidation_res = self._detect_consolidation(trace_result.paths)
        if consolidation_res:
            results.append(consolidation_res)

        # 4. RAPID_PEEL_LIKE_MOVEMENT Detection
        peel_res = self._detect_rapid_peel(trace_result.paths)
        if peel_res:
            results.append(peel_res)

        # 5. REPEATED_INTERACTION Detection
        repeated_res = self._detect_repeated_interactions(hops)
        if repeated_res:
            results.append(repeated_res)

        # 6. VASP_CONVERGENCE Detection
        if vasp_attribution:
            vasp_conv_res = self._detect_vasp_convergence(trace_result.paths, vasp_attribution)
            if vasp_conv_res:
                results.append(vasp_conv_res)

        return results

    def _detect_fan_out(
        self, hops: List[TraceHopItem], is_known_service: bool
    ) -> Optional[TypologyResult]:
        """Detect Fan-Out pattern (one wallet distributing to many recipients)."""
        if not hops:
            return None

        out_map: Dict[str, List[TraceHopItem]] = defaultdict(list)
        for h in hops:
            out_map[h.from_address].append(h)

        max_fan_sender = None
        max_recipients: Set[str] = set()
        max_hops: List[TraceHopItem] = []

        for sender, s_hops in out_map.items():
            recipients = {h.to_address for h in s_hops}
            if len(recipients) > len(max_recipients):
                max_recipients = recipients
                max_fan_sender = sender
                max_hops = s_hops

        if len(max_recipients) < 3:
            return None

        tot_amount = sum(h.amount for h in max_hops)
        tx_hashes = [h.tx_hash for h in max_hops]
        wallets = [max_fan_sender] + list(max_recipients)

        # Severity context: lower if sender is a known exchange
        severity = "MODERATE" if (len(max_recipients) < 5 or is_known_service) else "HIGH"
        desc = (
            f"Fan-Out pattern detected: Wallet {max_fan_sender[:10]}... rapidly distributed funds "
            f"to {len(max_recipients)} distinct recipient wallets totaling ${tot_amount:,.2f} USDT."
        )

        return TypologyResult(
            typology_id=f"typ-fanout-{max_fan_sender[:6]}",
            typology_name="FAN_OUT",
            severity=severity,
            description=desc,
            trigger_conditions=[
                f"Single wallet sent transfers to {len(max_recipients)} unique recipients (>= 3 threshold)"
            ],
            metrics={
                "sender_wallet": max_fan_sender,
                "recipient_count": len(max_recipients),
                "total_amount": round(tot_amount, 2),
                "transfer_count": len(max_hops),
                "recipient_ratio": round(len(max_recipients) / max(1, len(max_hops)), 2),
            },
            supporting_transactions=tx_hashes,
            supporting_wallets=wallets,
            supporting_paths=[],
            confidence=0.85 if not is_known_service else 0.60,
            is_known_service=is_known_service,
        )

    def _detect_fan_in(
        self, hops: List[TraceHopItem], is_known_service: bool
    ) -> Optional[TypologyResult]:
        """Detect Fan-In pattern (many wallets transferring into a single wallet)."""
        if not hops:
            return None

        in_map: Dict[str, List[TraceHopItem]] = defaultdict(list)
        for h in hops:
            in_map[h.to_address].append(h)

        max_recipient = None
        max_sources: Set[str] = set()
        max_hops: List[TraceHopItem] = []

        for recipient, r_hops in in_map.items():
            sources = {h.from_address for h in r_hops}
            if len(sources) > len(max_sources):
                max_sources = sources
                max_recipient = recipient
                max_hops = r_hops

        if len(max_sources) < 3:
            return None

        tot_amount = sum(h.amount for h in max_hops)
        tx_hashes = [h.tx_hash for h in max_hops]
        wallets = list(max_sources) + [max_recipient]

        severity = "MODERATE" if (len(max_sources) < 5 or is_known_service) else "HIGH"
        desc = (
            f"Fan-In pattern detected: Wallet {max_recipient[:10]}... received transfers "
            f"from {len(max_sources)} distinct source wallets totaling ${tot_amount:,.2f} USDT."
        )

        return TypologyResult(
            typology_id=f"typ-fanin-{max_recipient[:6]}",
            typology_name="FAN_IN",
            severity=severity,
            description=desc,
            trigger_conditions=[
                f"Single recipient wallet aggregated funds from {len(max_sources)} unique source wallets (>= 3 threshold)"
            ],
            metrics={
                "recipient_wallet": max_recipient,
                "source_wallet_count": len(max_sources),
                "total_amount": round(tot_amount, 2),
                "transfer_count": len(max_hops),
                "concentration_ratio": round(len(max_sources) / max(1, len(max_hops)), 2),
            },
            supporting_transactions=tx_hashes,
            supporting_wallets=wallets,
            supporting_paths=[],
            confidence=0.85 if not is_known_service else 0.60,
            is_known_service=is_known_service,
        )

    def _detect_consolidation(self, paths: List[TracePathDetail]) -> Optional[TypologyResult]:
        """Detect Consolidation (multiple downstream branches converging into a single wallet)."""
        if len(paths) < 2:
            return None

        terminal_map: Dict[str, List[TracePathDetail]] = defaultdict(list)
        for p in paths:
            if p.wallet_sequence:
                term = p.wallet_sequence[-1]
                terminal_map[term].append(p)

        converged_wallet = None
        converged_paths: List[TracePathDetail] = []
        for term, p_list in terminal_map.items():
            if len(p_list) >= 2:
                converged_wallet = term
                converged_paths = p_list
                break

        if not converged_wallet or len(converged_paths) < 2:
            return None

        path_ids = [p.path_id for p in converged_paths]
        tx_hashes = []
        wallets = set()
        for p in converged_paths:
            for h in p.hops:
                tx_hashes.append(h.tx_hash)
                wallets.add(h.from_address)
                wallets.add(h.to_address)

        desc = (
            f"Consolidation pattern detected: {len(converged_paths)} independent flow branches "
            f"converge into downstream target wallet {converged_wallet[:10]}..."
        )

        return TypologyResult(
            typology_id=f"typ-cons-{converged_wallet[:6]}",
            typology_name="CONSOLIDATION",
            severity="HIGH",
            description=desc,
            trigger_conditions=[
                f"{len(converged_paths)} distinct flow paths terminate at identical destination wallet"
            ],
            metrics={
                "converged_wallet": converged_wallet,
                "converging_branch_count": len(converged_paths),
                "path_ids": path_ids,
            },
            supporting_transactions=list(dict.fromkeys(tx_hashes)),
            supporting_wallets=list(wallets),
            supporting_paths=path_ids,
            confidence=0.90,
        )

    def _detect_rapid_peel(self, paths: List[TracePathDetail]) -> Optional[TypologyResult]:
        """Detect Rapid Peel-Like Movement (sequential downstream transfers with short time gaps and high value retention)."""
        qualifying_paths: List[TracePathDetail] = []

        for p in paths:
            if p.hop_count >= 2 and p.value_retention_percent >= 70.0:
                avg_delta = p.elapsed_time_seconds / max(1, p.hop_count)
                if avg_delta <= 1800.0:  # <= 30 mins per hop
                    qualifying_paths.append(p)

        if not qualifying_paths:
            return None

        best_path = max(qualifying_paths, key=lambda x: x.hop_count)
        avg_delta = best_path.elapsed_time_seconds / max(1, best_path.hop_count)

        tx_hashes = [h.tx_hash for h in best_path.hops if h.tx_hash]

        desc = (
            f"Rapid Peel-Like Movement detected: Observed {best_path.hop_count} sequential downstream transfers "
            f"with average delta_t of {avg_delta:.1f}s and {best_path.value_retention_percent:.1f}% value retention."
        )

        return TypologyResult(
            typology_id=f"typ-peel-{best_path.path_id[:6]}",
            typology_name="RAPID_PEEL_LIKE_MOVEMENT",
            severity="HIGH" if best_path.hop_count >= 3 else "MODERATE",
            description=desc,
            trigger_conditions=[
                f"Sequential downstream movement over {best_path.hop_count} hops with average gap {avg_delta:.1f}s and high value retention ({best_path.value_retention_percent:.1f}%)"
            ],
            metrics={
                "hop_count": best_path.hop_count,
                "initial_amount": best_path.initial_amount,
                "final_amount": best_path.final_amount,
                "value_retention_percent": best_path.value_retention_percent,
                "elapsed_time_seconds": best_path.elapsed_time_seconds,
                "average_delta_t_seconds": round(avg_delta, 1),
            },
            supporting_transactions=tx_hashes,
            supporting_wallets=best_path.wallet_sequence,
            supporting_paths=[best_path.path_id],
            confidence=0.88,
        )

    def _detect_repeated_interactions(self, hops: List[TraceHopItem]) -> Optional[TypologyResult]:
        """Detect Repeated Interactions (multiple transfers between the same wallet pair)."""
        pair_map: Dict[Tuple[str, str], List[TraceHopItem]] = defaultdict(list)
        for h in hops:
            pair_map[(h.from_address, h.to_address)].append(h)

        repeated_pair = None
        max_pair_hops: List[TraceHopItem] = []
        for pair, p_hops in pair_map.items():
            if len(p_hops) >= 2 and len(p_hops) > len(max_pair_hops):
                repeated_pair = pair
                max_pair_hops = p_hops

        if not repeated_pair or len(max_pair_hops) < 2:
            return None

        from_w, to_w = repeated_pair
        tot_val = sum(h.amount for h in max_pair_hops)
        tx_hashes = [h.tx_hash for h in max_pair_hops]

        desc = (
            f"Repeated Interaction detected: Identified {len(max_pair_hops)} transfers "
            f"between wallet {from_w[:8]}... and wallet {to_w[:8]}... totaling ${tot_val:,.2f} USDT."
        )

        return TypologyResult(
            typology_id=f"typ-repeat-{from_w[:6]}",
            typology_name="REPEATED_INTERACTION",
            severity="MODERATE",
            description=desc,
            trigger_conditions=[
                f"Repeated interaction between wallet pair ({len(max_pair_hops)} transfers)"
            ],
            metrics={
                "from_wallet": from_w,
                "to_wallet": to_w,
                "transfer_count": len(max_pair_hops),
                "total_value": round(tot_val, 2),
            },
            supporting_transactions=tx_hashes,
            supporting_wallets=[from_w, to_w],
            supporting_paths=[],
            confidence=0.80,
        )

    def _detect_vasp_convergence(
        self, paths: List[TracePathDetail], vasp_attribution: Any
    ) -> Optional[TypologyResult]:
        """Detect VASP Convergence (multiple paths converging on a known VASP endpoint)."""
        if not vasp_attribution or not vasp_attribution.candidates:
            return None

        top_cand = vasp_attribution.candidates[0]
        if top_cand.attribution_confidence < 40.0:
            return None

        converging_paths = [p for p in paths if p.wallet_sequence and top_cand.endpoint_address in p.wallet_sequence]
        if len(converging_paths) < 1:
            return None

        desc = (
            f"VASP Convergence detected: Fund flow graph terminates at candidate VASP '{top_cand.candidate_name}' "
            f"({top_cand.endpoint_address}) with {top_cand.confidence_band} confidence (Score: {top_cand.attribution_confidence:.1f}/100)."
        )

        return TypologyResult(
            typology_id=f"typ-vaspconv-{top_cand.endpoint_address[:6]}",
            typology_name="VASP_CONVERGENCE",
            severity="HIGH" if top_cand.confidence_band in ["HIGH", "MODERATE"] else "MODERATE",
            description=desc,
            trigger_conditions=[
                f"Path flow converges on attributed VASP endpoint '{top_cand.candidate_name}' (Confidence: {top_cand.attribution_confidence:.1f}/100)"
            ],
            metrics={
                "candidate_name": top_cand.candidate_name,
                "endpoint_address": top_cand.endpoint_address,
                "attribution_confidence": top_cand.attribution_confidence,
                "confidence_band": top_cand.confidence_band,
                "converging_path_count": len(converging_paths),
            },
            supporting_transactions=top_cand.supporting_transactions,
            supporting_wallets=top_cand.supporting_wallets,
            supporting_paths=top_cand.path_sequence,
            confidence=round(top_cand.source_confidence, 2),
            is_known_service=True,
        )
