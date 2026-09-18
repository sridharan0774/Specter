import logging
from typing import Dict, Any, Tuple, Optional, List
from app.vasp.matcher import MatchedCandidate
from app.models.vasp import VASPRecord

logger = logging.getLogger("specter.vasp.scorer")

SCORING_MODEL_VERSION = "vasp-score-v1"


class ScoredCandidate:
    """Internal container for a scored VASP candidate."""

    def __init__(
        self,
        candidate_name: str,
        endpoint_address: str,
        chain: str,
        endpoint_hop_distance: int,
        attribution_type: str,
        source_confidence: float,
        attribution_confidence: float,
        confidence_band: str,
        score_components: Dict[str, float],
        evidence_summary: list,
        supporting_transactions: list,
        supporting_wallets: list,
        path_sequence: list,
        source_metadata: Dict[str, Any],
        matched_candidate: MatchedCandidate,
        entity_role: str = "VASP",
        match_position: str = "TERMINAL_ENDPOINT",
        is_terminal_endpoint: bool = True,
        value_transferred: float = 0.0,
        value_retention_percent: float = 0.0,
        temporal_proximity_seconds: float = 0.0,
        path_convergence_count: int = 1,
        why_this_vasp: Optional[List[str]] = None,
    ):
        self.candidate_name = candidate_name
        self.endpoint_address = endpoint_address
        self.chain = chain
        self.endpoint_hop_distance = endpoint_hop_distance
        self.attribution_type = attribution_type
        self.source_confidence = source_confidence
        self.attribution_confidence = attribution_confidence
        self.confidence_band = confidence_band
        self.score_components = score_components
        self.evidence_summary = evidence_summary
        self.supporting_transactions = supporting_transactions
        self.supporting_wallets = supporting_wallets
        self.path_sequence = path_sequence
        self.source_metadata = source_metadata
        self.matched_candidate = matched_candidate
        self.entity_role = entity_role
        self.match_position = match_position
        self.is_terminal_endpoint = is_terminal_endpoint
        self.value_transferred = value_transferred
        self.value_retention_percent = value_retention_percent
        self.temporal_proximity_seconds = temporal_proximity_seconds
        self.path_convergence_count = path_convergence_count
        self.why_this_vasp = why_this_vasp or []


class VASPScorer:
    """
    Calculates analytical VASP Attribution Confidence Scores (0-100) using
    weighted explainable signals and source quality metrics.
    Strictly distinguishes terminal endpoints from intermediate associations.
    """

    def score_candidate(self, matched: MatchedCandidate) -> ScoredCandidate:
        """Score a matched candidate based on multi-signal evidence."""
        score_components: Dict[str, float] = {}
        evidence_statements: list = []

        # 1. Source Confidence (0.0 to 1.0)
        source_conf = self._calculate_source_confidence(matched.vasp_record)

        # 2. Signal 1: Entity Address Match (30 pts max for terminal; 10 pts for intermediate)
        sig1_score, sig1_reason = self._score_entity_match(matched)
        score_components["entity_address_match"] = sig1_score
        evidence_statements.append(sig1_reason)

        # 3. Signal 2: Source Quality Level (20 pts max)
        sig2_score, sig2_reason = self._score_source_quality(matched.vasp_record)
        score_components["source_quality_level"] = sig2_score
        evidence_statements.append(sig2_reason)

        # 4. Signal 3: Endpoint Proximity / Hop Distance (15 pts max)
        sig3_score, sig3_reason = self._score_hop_proximity(matched.hop_distance)
        score_components["endpoint_proximity"] = sig3_score
        evidence_statements.append(sig3_reason)

        # 5. Signal 4: Deposit / Hot Wallet Role Evidence (15 pts max for terminal; 3 pts for intermediate)
        sig4_score, sig4_reason = self._score_wallet_role(matched)
        score_components["wallet_role_evidence"] = sig4_score
        evidence_statements.append(sig4_reason)

        # 6. Signal 5: Value Retention / Continuity (10 pts max)
        sig5_score, sig5_reason = self._score_value_continuity(matched)
        score_components["value_retention"] = sig5_score
        evidence_statements.append(sig5_reason)

        # 7. Signal 6: Temporal Continuity / Velocity (5 pts max)
        sig6_score, sig6_reason = self._score_temporal_velocity(matched)
        score_components["temporal_velocity"] = sig6_score
        evidence_statements.append(sig6_reason)

        # 8. Signal 7: Path Convergence & Interaction Frequency (5 pts max)
        sig7_score, sig7_reason = self._score_path_convergence(matched)
        score_components["path_convergence"] = sig7_score
        evidence_statements.append(sig7_reason)

        # Sum total attribution score (capped at 100.0)
        raw_score = sum(score_components.values())
        attribution_confidence = round(min(100.0, max(0.0, raw_score)), 2)

        # Determine confidence band
        confidence_band = self._classify_confidence_band(attribution_confidence)

        # Construct concise, explainable "WHY THIS VASP?" items grounded strictly in trace data
        why_this_vasp = self._build_why_this_vasp(matched)

        source_metadata = {
            "source": matched.vasp_record.source if matched.vasp_record else "Unknown",
            "source_url": matched.vasp_record.source_url if matched.vasp_record else None,
            "source_reference": matched.vasp_record.source_reference if matched.vasp_record else None,
            "source_quality_level": matched.vasp_record.source_quality_level if matched.vasp_record else 5,
            "verified_at": matched.vasp_record.verified_at.isoformat() if (matched.vasp_record and matched.vasp_record.verified_at) else None,
        }

        return ScoredCandidate(
            candidate_name=matched.candidate_name,
            endpoint_address=matched.matching_address,
            chain=matched.chain,
            endpoint_hop_distance=matched.hop_distance,
            attribution_type=matched.attribution_type,
            source_confidence=source_conf,
            attribution_confidence=attribution_confidence,
            confidence_band=confidence_band,
            score_components=score_components,
            evidence_summary=evidence_statements,
            supporting_transactions=matched.supporting_transactions,
            supporting_wallets=matched.supporting_wallets,
            path_sequence=matched.path_sequence,
            source_metadata=source_metadata,
            matched_candidate=matched,
            entity_role=matched.entity_role,
            match_position=matched.match_position,
            is_terminal_endpoint=matched.is_terminal_endpoint,
            value_transferred=matched.value_transferred,
            value_retention_percent=matched.value_retention_percent,
            temporal_proximity_seconds=matched.temporal_proximity_seconds,
            path_convergence_count=matched.path_convergence_count,
            why_this_vasp=why_this_vasp,
        )

    def _build_why_this_vasp(self, matched: MatchedCandidate) -> List[str]:
        """Constructs concise, evidence-grounded points answering 'WHY THIS VASP?'."""
        items: List[str] = []

        # 1. Address match & endpoint status
        if matched.is_terminal_endpoint:
            items.append(f"Known VASP-associated address matched at terminal traced endpoint ({matched.candidate_name})")
        else:
            items.append(f"Known VASP-associated address matched at intermediate hop (funds exited to downstream wallets)")

        # 2. Match position
        pos_str = "terminal traced endpoint" if matched.is_terminal_endpoint else "intermediate path node"
        items.append(f"Match occurs at {pos_str} ({matched.matching_address})")

        # 3. Hop distance
        items.append(f"{matched.hop_distance} hop(s) distance from suspicious wallet")

        # 4. Value transferred & continuity
        retention = matched.value_retention_percent
        if matched.value_transferred > 0:
            items.append(f"{retention:.1f}% of traced value reaches the endpoint (${matched.value_transferred:,.2f} transferred)")
        else:
            items.append(f"{retention:.1f}% of traced value reaches the endpoint")

        # 5. Timing
        sec = matched.temporal_proximity_seconds
        if matched.hop_distance == 1 or all(p.hop_count == 1 for p in matched.paths_involved):
            items.append("Transaction timing is consistent with rapid movement based on observed transaction timestamps (direct 1-hop transfer)")
        elif sec <= 0:
            items.append("Transaction timing is consistent with rapid movement based on observed transaction timestamps (same block execution)")
        elif sec < 5:
            items.append("Transaction timing is consistent with rapid movement based on observed transaction timestamps (<5s transfer interval)")
        elif sec <= 60:
            items.append(f"Transaction timing supports the path (rapid transfer within {sec:.0f} seconds)")
        elif sec <= 3600:
            items.append(f"Transaction timing supports the path ({sec/60:.1f} minutes transfer window)")
        elif sec <= 86400:
            items.append(f"Transaction timing supports the path ({sec/3600:.1f} hours transfer window)")
        else:
            items.append(f"Transaction timing supports the path ({sec/86400:.1f} days transfer window)")

        # 6. Source provenance
        src_name = matched.vasp_record.source if matched.vasp_record else "Unknown"
        lvl = matched.vasp_record.source_quality_level if matched.vasp_record else 5
        items.append(f"Source intelligence has Level {lvl} provenance ({src_name})")

        # 7. Path convergence
        num_paths = matched.path_convergence_count
        if num_paths >= 2:
            items.append(f"{num_paths} traced paths converge on this entity")
        else:
            items.append("Single coherent fund flow path directly connects to this endpoint")

        return items

    def _calculate_source_confidence(self, record: Optional[VASPRecord]) -> float:
        if not record:
            return 0.0
        level_multipliers = {1: 1.0, 2: 0.95, 3: 0.85, 4: 0.60, 5: 0.0}
        mult = level_multipliers.get(record.source_quality_level, 0.0)
        raw_conf = getattr(record, "confidence", 1.0) or 1.0
        return round(min(1.0, max(0.0, raw_conf * mult)), 4)

    def _score_entity_match(self, matched: MatchedCandidate) -> Tuple[float, str]:
        if matched.is_terminal_endpoint:
            return 30.0, f"Direct terminal endpoint match for known address of {matched.candidate_name} (+30.0 pts)."
        else:
            return 10.0, f"Intermediate path association with registered entity {matched.candidate_name}; funds continued downstream (+10.0 pts)."

    def _score_source_quality(self, record: Optional[VASPRecord]) -> Tuple[float, str]:
        if not record:
            return 0.0, "Unverified or unknown source intelligence (+0.0 pts)."
        level = record.source_quality_level
        source_name = record.source
        if level == 1:
            return 20.0, f"Level 1 Official/First-party intelligence source ({source_name}) (+20.0 pts)."
        elif level == 2:
            return 17.0, f"Level 2 Highly trusted intelligence provider source ({source_name}) (+17.0 pts)."
        elif level == 3:
            return 12.0, f"Level 3 Established public explorer/label source ({source_name}) (+12.0 pts)."
        elif level == 4:
            return 5.0, f"Level 4 Research/Public attribution source ({source_name}) (+5.0 pts)."
        else:
            return 0.0, f"Level 5 Unverified/Weak source intelligence ({source_name}) (+0.0 pts)."

    def _score_hop_proximity(self, hop_distance: int) -> Tuple[float, str]:
        if hop_distance == 1:
            return 15.0, "Immediate 1-hop direct transfer from suspicious starting wallet (+15.0 pts)."
        elif hop_distance == 2:
            return 12.0, "Close proximity 2-hop flow from suspicious starting wallet (+12.0 pts)."
        elif hop_distance == 3:
            return 9.0, "3-hop distance traversal to candidate endpoint (+9.0 pts)."
        elif hop_distance == 4:
            return 6.0, "4-hop distance traversal to candidate endpoint (+6.0 pts)."
        else:
            return 3.0, f"{hop_distance}-hop distance traversal to candidate endpoint (+3.0 pts)."

    def _score_wallet_role(self, matched: MatchedCandidate) -> Tuple[float, str]:
        attr_type = matched.attribution_type
        if matched.is_terminal_endpoint:
            if attr_type == "KNOWN_DEPOSIT_ENDPOINT":
                return 15.0, f"Candidate endpoint verified as active user deposit aggregation wallet (+15.0 pts)."
            elif attr_type == "KNOWN_HOT_WALLET":
                return 15.0, f"Candidate endpoint verified as main exchange omnibus hot wallet (+15.0 pts)."
            elif attr_type == "KNOWN_CUSTODIAL_WALLET":
                return 12.0, f"Candidate endpoint verified as custodial operational exchange wallet (+12.0 pts)."
            else:
                return 10.0, f"Candidate endpoint is a terminal wallet in the trace flow (+10.0 pts)."
        else:
            return 3.0, f"Candidate address serves as an intermediate path relay (+3.0 pts)."

    def _score_value_continuity(self, matched: MatchedCandidate) -> Tuple[float, str]:
        if not matched.paths_involved:
            return 5.0, "Moderate value retention across trace path (+5.0 pts)."

        max_retention = max([p.value_retention_percent for p in matched.paths_involved])
        if max_retention >= 90.0:
            return 10.0, f"High value retention ({max_retention:.1f}%) preserved along fund flow path (+10.0 pts)."
        elif max_retention >= 75.0:
            return 8.0, f"Substantial value retention ({max_retention:.1f}%) preserved along path (+8.0 pts)."
        elif max_retention >= 50.0:
            return 6.0, f"Moderate value retention ({max_retention:.1f}%) preserved along path (+6.0 pts)."
        elif max_retention >= 25.0:
            return 4.0, f"Partial value retention ({max_retention:.1f}%) preserved along path (+4.0 pts)."
        else:
            return 2.0, f"Low value retention ({max_retention:.1f}%) along path (+2.0 pts)."

    def _score_temporal_velocity(self, matched: MatchedCandidate) -> Tuple[float, str]:
        if not matched.paths_involved:
            return 3.0, "Standard transfer velocity along path (+3.0 pts)."

        min_elapsed = min([p.elapsed_time_seconds for p in matched.paths_involved])
        if matched.hop_distance == 1 or all(p.hop_count == 1 for p in matched.paths_involved):
            return 5.0, "Direct 1-hop transfer; timing is consistent with rapid movement based on observed transaction timestamps (+5.0 pts)."
        elif min_elapsed <= 60:
            return 5.0, "Rapid fund velocity; timing is consistent with rapid movement based on observed transaction timestamps (+5.0 pts)."
        elif min_elapsed <= 600:  # < 10 mins
            return 5.0, f"Rapid fund velocity (elapsed time {min_elapsed/60:.1f} mins) (+5.0 pts)."
        elif min_elapsed <= 3600:  # < 1 hour
            return 4.0, f"Fast fund velocity (elapsed time {min_elapsed/60:.1f} mins) (+4.0 pts)."
        elif min_elapsed <= 86400:  # < 24 hours
            return 3.0, f"Standard multi-hour flow (elapsed time {min_elapsed/3600:.1f} hours) (+3.0 pts)."
        else:
            return 1.0, f"Slow multi-day flow (elapsed time {min_elapsed/86400:.1f} days) (+1.0 pt)."

    def _score_path_convergence(self, matched: MatchedCandidate) -> Tuple[float, str]:
        num_paths = len(matched.paths_involved)
        if num_paths >= 2:
            return 5.0, f"Path convergence detected: {num_paths} traced flow paths terminate at {matched.candidate_name} (+5.0 pts)."
        else:
            return 2.5, f"Single path flow identified to {matched.candidate_name} (+2.5 pts)."

    def _classify_confidence_band(self, score: float) -> str:
        """
        Classifies confidence band strictly per SPECTER guidelines:
        - HIGH: 80 - 100
        - MODERATE: 60 - 79
        - LOW: 40 - 59
        - INSUFFICIENT: < 40
        """
        if score >= 80.0:
            return "HIGH"
        elif score >= 60.0:
            return "MODERATE"
        elif score >= 40.0:
            return "LOW"
        else:
            return "INSUFFICIENT"
