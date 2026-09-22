import logging
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.risk import RiskIndicatorResponse, RiskIndicatorItem
from app.schemas.trace import TraceResultResponse
from app.schemas.velocity import VelocityAnalysisResponse
from app.schemas.typology import TypologyAnalysisResponse
from app.schemas.vasp import VASPAttributionResponse

logger = logging.getLogger("specter.intelligence.risk_engine")


class ExplainableGraphRiskEngine:
    """
    Explainable Graph Risk Engine (EGRE_V1) for SPECTER (SIH Problem Statement 26182).
    
    Evaluates observable transaction graph features across 6 distinct risk dimensions:
    1. ENTITY_EXPOSURE (Cap: 30.0)
    2. TEMPORAL (Cap: 25.0)
    3. OBFUSCATION (Cap: 25.0)
    4. GRAPH_STRUCTURE (Cap: 20.0)
    5. VALUE_FLOW (Cap: 15.0)
    6. BEHAVIOURAL (Cap: 15.0)
    
    Principles:
    - OBSERVE -> MEASURE -> DETECT -> SCORE -> EXPLAIN
    - Strict separation of Risk Score (0-100) vs VASP Attribution Score (0-100).
    - Correlation control via dimension caps to prevent double-counting.
    - Explicit classification: OBSERVED, INFERRED, HEURISTIC.
    - Assessment Status: ASSESSED vs INSUFFICIENT_EVIDENCE.
    - Deterministic, 100% reproducible scoring without LLM dependencies.
    """

    CALCULATION_VERSION = "EGRE_V1"

    DIMENSION_CAPS: Dict[str, float] = {
        "ENTITY_EXPOSURE": 30.0,
        "TEMPORAL": 25.0,
        "OBFUSCATION": 25.0,
        "GRAPH_STRUCTURE": 20.0,
        "VALUE_FLOW": 15.0,
        "BEHAVIOURAL": 15.0,
    }

    def evaluate_risk(
        self,
        trace_result: TraceResultResponse,
        velocity_resp: VelocityAnalysisResponse,
        typology_resp: TypologyAnalysisResponse,
        vasp_resp: Optional[VASPAttributionResponse] = None,
        case_id: Optional[str] = None,
    ) -> RiskIndicatorResponse:
        """
        Executes full EGRE_V1 evaluation returning itemized, explainable risk indicators,
        dimension breakdown, correlation control, and contextual mitigations.
        """
        trace_id = trace_result.trace_id
        starting_wallet = trace_result.starting_wallet
        chain = trace_result.chain or "TRON"
        asset = trace_result.asset or "USDT"

        total_txs = trace_result.total_transactions_analyzed
        total_paths = trace_result.total_paths_found
        total_wallets = trace_result.total_wallets_discovered

        # Extract metrics safely whether dict or object
        metrics_dict = velocity_resp.metrics if isinstance(velocity_resp.metrics, dict) else (getattr(velocity_resp.metrics, "__dict__", {}) or {})
        transfer_count = int(metrics_dict.get("transfer_count") or 0)
        min_delta = metrics_dict.get("minimum_delta_t")
        avg_delta = metrics_dict.get("average_delta_t")
        recipients_count = int(metrics_dict.get("unique_recipients") or 0)
        total_vol = float(metrics_dict.get("total_amount") or 0.0)
        velocity_score = float(metrics_dict.get("velocity_score") or 0.0)

        # Check for INSUFFICIENT_EVIDENCE condition
        if total_txs <= 1 and total_paths <= 1 and transfer_count <= 1:
            return RiskIndicatorResponse(
                trace_id=trace_id,
                case_id=case_id,
                starting_wallet=starting_wallet,
                chain=chain,
                asset=asset,
                risk_score=None,
                raw_risk_score=None,
                contextual_risk_score=None,
                risk_level=None,
                assessment_status="INSUFFICIENT_EVIDENCE",
                calculation_version=self.CALCULATION_VERSION,
                contextual_interpretation="Only one observable transaction was available. The available history is insufficient for reliable behavioural and graph risk assessment.",
                dimension_scores={},
                indicators=[],
                component_contributions={},
                contributing_factors=["INSUFFICIENT_TRANSACTION_HISTORY"],
                is_known_service_entity=False,
                service_entity_context=False,
                false_positive_mitigations=["Insufficient trace history available to evaluate graph risk indicators."],
            )

        indicators: List[RiskIndicatorItem] = []
        raw_dimension_contributions: Dict[str, List[Tuple[str, float]]] = {
            "ENTITY_EXPOSURE": [],
            "TEMPORAL": [],
            "OBFUSCATION": [],
            "GRAPH_STRUCTURE": [],
            "VALUE_FLOW": [],
            "BEHAVIOURAL": [],
        }

        all_tx_hashes: List[str] = []
        all_path_ids: List[str] = [p.path_id for p in trace_result.paths]

        for p in trace_result.paths:
            for h in p.hops:
                if h.tx_hash and h.tx_hash not in all_tx_hashes:
                    all_tx_hashes.append(h.tx_hash)

        # ----------------------------------------------------
        # 1. TEMPORAL DIMENSION INDICATORS
        # ----------------------------------------------------
        if min_delta is not None and float(min_delta) <= 120.0 and transfer_count >= 2:
            min_delta_flt = float(min_delta)
            contrib = 15.0 if min_delta_flt <= 30.0 else 10.0
            ind = RiskIndicatorItem(
                indicator_id="RAPID_MOVEMENT",
                indicator_name="Rapid Successive Fund Movement",
                dimension="TEMPORAL",
                classification="OBSERVED",
                detection_rule="Minimum inter-transfer interval delta_t <= 120 seconds",
                observed_value=f"Minimum transfer interval: {min_delta_flt:.1f}s across {transfer_count} transfers",
                threshold_reference="Threshold: <= 120s",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:3],
                supporting_paths=all_path_ids[:2],
            )
            indicators.append(ind)
            raw_dimension_contributions["TEMPORAL"].append(("RAPID_MOVEMENT", contrib))

        if transfer_count >= 4 or velocity_score >= 50.0:
            contrib = 10.0
            ind = RiskIndicatorItem(
                indicator_id="HIGH_TRANSACTION_VELOCITY",
                indicator_name="High Transaction Velocity Pattern",
                dimension="TEMPORAL",
                classification="OBSERVED",
                detection_rule="Observed transfer count >= 4 or calculated velocity score >= 50.0",
                observed_value=f"Transfer count: {transfer_count}, Velocity score: {velocity_score:.1f}",
                threshold_reference="Threshold: >= 4 transfers",

                contribution=contrib,
                supporting_transactions=all_tx_hashes[:5],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["TEMPORAL"].append(("HIGH_TRANSACTION_VELOCITY", contrib))

        # ----------------------------------------------------
        # 2. GRAPH STRUCTURE DIMENSION INDICATORS
        # ----------------------------------------------------
        max_hops = max([p.hop_count for p in trace_result.paths], default=1)
        if max_hops >= 3:
            contrib = 10.0 if max_hops >= 4 else 7.0
            ind = RiskIndicatorItem(
                indicator_id="MULTI_HOP_FLOW",
                indicator_name="Multi-Hop Deep Layering Path",
                dimension="GRAPH_STRUCTURE",
                classification="OBSERVED",
                detection_rule="Trace path depth >= 3 hops",
                observed_value=f"Maximum path depth: {max_hops} hops across {total_paths} paths",
                threshold_reference="Threshold: >= 3 hops",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:4],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["GRAPH_STRUCTURE"].append(("MULTI_HOP_FLOW", contrib))

        if recipients_count >= 4:
            contrib = 8.0
            ind = RiskIndicatorItem(
                indicator_id="FAN_OUT",
                indicator_name="Fan-Out Transfer Dispersion",
                dimension="GRAPH_STRUCTURE",
                classification="OBSERVED",
                detection_rule="Outbound transfers disperse to >= 4 distinct recipient wallets",
                observed_value=f"Dispersed to {recipients_count} distinct recipient wallets",
                threshold_reference="Threshold: >= 4 recipient wallets",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:4],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["GRAPH_STRUCTURE"].append(("FAN_OUT", contrib))

        # Check consolidation (multiple paths converging onto destination)
        dest_wallets = [p.wallet_sequence[-1] for p in trace_result.paths if len(p.wallet_sequence) > 1]
        unique_dests = set(dest_wallets)
        if total_paths >= 3 and len(unique_dests) < total_paths:
            contrib = 8.0
            ind = RiskIndicatorItem(
                indicator_id="CONSOLIDATION",
                indicator_name="Fund Flow Consolidation",
                dimension="GRAPH_STRUCTURE",
                classification="OBSERVED",
                detection_rule="Multiple distinct transaction paths converge onto single destination wallet",
                observed_value=f"{total_paths} distinct paths converging onto {len(unique_dests)} endpoint wallet(s)",
                threshold_reference="Threshold: >= 3 paths converging",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:4],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["GRAPH_STRUCTURE"].append(("CONSOLIDATION", contrib))

        # ----------------------------------------------------
        # 3. VALUE FLOW DIMENSION INDICATORS
        # ----------------------------------------------------
        max_retention = max([p.value_retention_percent for p in trace_result.paths], default=0.0)

        if max_retention >= 75.0 or total_vol >= 25000.0:
            contrib = 10.0 if total_vol >= 100000.0 else 7.0
            ind = RiskIndicatorItem(
                indicator_id="VALUE_CONCENTRATION",
                indicator_name="High Value Concentration & Retention",
                dimension="VALUE_FLOW",
                classification="OBSERVED",
                detection_rule="Value retention >= 75% or total transferred volume >= $25,000",
                observed_value=f"Max value retention: {max_retention:.1f}%, Total volume: ${total_vol:,.2f}",
                threshold_reference="Threshold: >= 75% retention or >= $25,000",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:3],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["VALUE_FLOW"].append(("VALUE_CONCENTRATION", contrib))


        # ----------------------------------------------------
        # 4. BEHAVIOURAL DIMENSION INDICATORS
        # ----------------------------------------------------
        if total_txs > total_wallets and total_wallets >= 2:
            contrib = 8.0
            ind = RiskIndicatorItem(
                indicator_id="REPEATED_INTERACTION",
                indicator_name="Repeated Wallet-Pair Interaction",
                dimension="BEHAVIOURAL",
                classification="OBSERVED",
                detection_rule="Multiple distinct transaction records executed between identical wallet pairs",
                observed_value=f"{total_txs} transactions executed across {total_wallets} total wallets",
                threshold_reference="Threshold: tx_count > wallet_count",
                contribution=contrib,
                supporting_transactions=all_tx_hashes[:3],
                supporting_paths=all_path_ids,
            )
            indicators.append(ind)
            raw_dimension_contributions["BEHAVIOURAL"].append(("REPEATED_INTERACTION", contrib))

        # ----------------------------------------------------
        # 5. OBFUSCATION DIMENSION INDICATORS
        # ----------------------------------------------------
        # Check cross-chain typology / bridge
        for typ in typology_resp.typologies:
            if "BRIDGE" in typ.typology_name.upper() or "CROSS_CHAIN" in typ.typology_name.upper():
                contrib = 12.0
                ind = RiskIndicatorItem(
                    indicator_id="CROSS_CHAIN_MOVEMENT",
                    indicator_name="Cross-Chain Bridge Interaction",
                    dimension="OBFUSCATION",
                    classification="INFERRED",
                    detection_rule="Observed transaction sequence involves cross-chain bridge or asset swap protocol",
                    observed_value=f"Detected typology: {typ.typology_name}",
                    threshold_reference="Bridge protocol structural match",
                    contribution=contrib,
                    supporting_transactions=typ.supporting_transactions,
                    supporting_paths=all_path_ids,
                )
                indicators.append(ind)
                raw_dimension_contributions["OBFUSCATION"].append(("CROSS_CHAIN_MOVEMENT", contrib))
                break

        # Check mixer heuristic pattern
        for typ in typology_resp.typologies:
            if "MIXER" in typ.typology_name.upper() or "PEEL" in typ.typology_name.upper():
                contrib = 15.0
                ind = RiskIndicatorItem(
                    indicator_id="POTENTIAL_MIXER_PATTERN",
                    indicator_name="Potential Mixer-Like Pattern",
                    dimension="OBFUSCATION",
                    classification="HEURISTIC",
                    detection_rule="Heuristic detection of rapid peeling, equal-value splitting, or obfuscation movement",
                    observed_value=f"Heuristic pattern match: {typ.typology_name} (Confidence: {typ.confidence:.2f})",
                    threshold_reference="Obfuscation pattern heuristic match",
                    contribution=contrib,
                    supporting_transactions=typ.supporting_transactions,
                    supporting_paths=all_path_ids,
                )
                indicators.append(ind)
                raw_dimension_contributions["OBFUSCATION"].append(("POTENTIAL_MIXER_PATTERN", contrib))
                break

        # ----------------------------------------------------
        # 6. ENTITY EXPOSURE DIMENSION INDICATORS
        # ----------------------------------------------------
        # Check high-risk entity exposure
        for typ in typology_resp.typologies:
            if "DARKNET" in typ.typology_name.upper() or "HIGH_RISK" in typ.typology_name.upper() or "RANSOMWARE" in typ.typology_name.upper():
                contrib = 25.0
                ind = RiskIndicatorItem(
                    indicator_id="KNOWN_HIGH_RISK_EXPOSURE",
                    indicator_name="Known High-Risk Entity Exposure",
                    dimension="ENTITY_EXPOSURE",
                    classification="INFERRED",
                    detection_rule="Direct or multi-hop exposure to verified high-risk or sanctioned entity",
                    observed_value=f"Matched entity typology: {typ.typology_name}",
                    threshold_reference="High-risk entity database match",
                    contribution=contrib,
                    supporting_transactions=typ.supporting_transactions,
                    supporting_paths=all_path_ids,
                )
                indicators.append(ind)
                raw_dimension_contributions["ENTITY_EXPOSURE"].append(("KNOWN_HIGH_RISK_EXPOSURE", contrib))
                break

        # ----------------------------------------------------
        # CORRELATION CONTROL & DIMENSION CAPPING
        # ----------------------------------------------------
        dimension_scores: Dict[str, float] = {}
        for dim, cap in self.DIMENSION_CAPS.items():
            raw_dim_sum = sum([item[1] for item in raw_dimension_contributions[dim]])
            # Apply per-dimension cap (Correlation Control)
            capped_score = round(min(cap, raw_dim_sum), 2)
            dimension_scores[dim.lower()] = capped_score

        # Unmitigated Raw Risk Score (sum of capped dimension scores, max 130)
        raw_risk_score = sum(dimension_scores.values())

        # ----------------------------------------------------
        # CONTEXTUAL MITIGATION LOGIC
        # ----------------------------------------------------
        is_known_service = False
        mitigations: List[str] = []

        top_vasp = vasp_resp.candidates[0] if (vasp_resp and vasp_resp.status == "RESOLVED" and vasp_resp.candidates) else None
        if top_vasp and top_vasp.attribution_confidence >= 50.0:
            is_known_service = True

        contextual_adjustment = 0.0
        if is_known_service:
            mitigations.append(f"Attributed to verified custodial VASP '{top_vasp.candidate_name if top_vasp else 'VASP'}'; movement reflects exchange endpoint context.")
            if not any(ind.indicator_id == "KNOWN_HIGH_RISK_EXPOSURE" for ind in indicators):
                contextual_adjustment += 15.0



        if total_vol < 500.0:
            contextual_adjustment += 5.0
            mitigations.append("Low transfer volume (< $500) reduces overall financial impact risk.")

        contextual_risk_score = max(0.0, raw_risk_score - contextual_adjustment)

        # Deterministic Final Risk Score (0 - 100)
        final_risk_score = round(min(100.0, contextual_risk_score), 2)

        # Risk Level Classification (0-24 LOW, 25-49 MODERATE, 50-74 HIGH, 75-100 VERY HIGH)
        if final_risk_score >= 75.0:
            risk_level = "VERY HIGH"
        elif final_risk_score >= 50.0:
            risk_level = "HIGH"
        elif final_risk_score >= 25.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        contributing_factors = [ind.indicator_name for ind in indicators]

        component_contributions = {
            ind.indicator_id.lower(): ind.contribution for ind in indicators
        }

        return RiskIndicatorResponse(
            trace_id=trace_id,
            case_id=case_id,
            starting_wallet=starting_wallet,
            chain=chain,
            asset=asset,
            risk_score=final_risk_score,
            raw_risk_score=round(raw_risk_score, 2),
            contextual_risk_score=round(contextual_risk_score, 2),
            risk_level=risk_level,
            assessment_status="ASSESSED",
            calculation_version=self.CALCULATION_VERSION,
            contextual_interpretation="Risk indicators represent observed transaction and graph patterns. They do not by themselves establish criminal activity, ownership, or illicit intent.",
            dimension_scores=dimension_scores,
            indicators=indicators,
            component_contributions=component_contributions,
            contributing_factors=contributing_factors,
            is_known_service_entity=is_known_service,
            service_entity_context=is_known_service,
            false_positive_mitigations=mitigations if mitigations else ["No false-positive mitigations were triggered."],
        )
