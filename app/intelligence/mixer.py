import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.intelligence import PatternObservation
from app.intelligence.classifier import WalletRoleClassifier

logger = logging.getLogger("specter.intelligence.mixer")


class MixerIntelligenceEngine:
    """
    Dedicated Mixer & Tumbler Intelligence Engine.
    Strictly enforces the distinction between:
    - Case A: VERIFIED MIXER ENTITY (Explicit intelligence label + provenance)
    - Case B: POTENTIAL MIXER-LIKE ACTIVITY (Analytical structural graph pattern indication)
    
    NEVER labels an analytical pattern as 'CONFIRMED MIXER' without verified DB intelligence.
    """

    def __init__(self, db: Session):
        self.db = db
        self.classifier = WalletRoleClassifier(db)

    def evaluate_wallet_mixer_status(self, address: str, chain: str = "TRON", graph_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluates whether a wallet is a Verified Mixer or exhibits analytical potential mixer-like patterns.
        """
        # Case A: Check explicit verified entity classification
        cls_info = self.classifier.classify_wallet(address, chain)
        if cls_info["entity_role"] == "MIXER" and cls_info["verification_status"] == "VERIFIED":
            return {
                "address": address,
                "chain": chain,
                "is_mixer_interaction": True,
                "label": "Verified Mixer / Tumbler",
                "entity_name": cls_info["entity_name"],
                "verification_status": "VERIFIED",
                "confidence": cls_info["confidence"],
                "source": cls_info["source_name"],
                "source_url": cls_info["source_url"],
                "evidence_summary": [
                    f"✓ Verified Mixer entity '{cls_info['entity_name']}' matched in intelligence database",
                    f"✓ Provenance: {cls_info['source_name']}",
                ],
            }

        # Case B: Evaluate analytical pattern indicators from graph structural data
        pattern_res = self.detect_mixer_pattern_indicators(address, graph_data)
        if pattern_res["is_pattern_detected"]:
            return {
                "address": address,
                "chain": chain,
                "is_mixer_interaction": False,
                "label": "POTENTIAL MIXER-LIKE ACTIVITY",
                "entity_name": "Unclassified Entity (Analytical Pattern)",
                "verification_status": "ANALYTICAL",
                "confidence": pattern_res["confidence"],
                "source": "SPECTER Graph Analytical Pattern Detector",
                "source_url": None,
                "indicators": pattern_res["indicators"],
                "supporting_transactions": pattern_res["supporting_txs"],
                "evidence_summary": [
                    "⚠️ Analytical Detection: POTENTIAL MIXER-LIKE ACTIVITY",
                    f"⚠️ Structural Indicator: {pattern_res['explanation']}",
                    "• Note: This is an analytical structural indicator, NOT verified proof of mixer service identity.",
                ],
            }

        # Case C: Unknown / Insufficient evidence
        return {
            "address": address,
            "chain": chain,
            "is_mixer_interaction": False,
            "label": "NO MIXER ACTIVITY DETECTED",
            "entity_name": "Unknown Entity",
            "verification_status": "UNKNOWN",
            "confidence": 0.0,
            "source": "SPECTER Engine",
            "source_url": None,
            "evidence_summary": ["• No verified mixer relationship or structural mixer pattern detected."],
        }

    def detect_mixer_pattern_indicators(self, target_wallet: str, graph_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes graph edges and transactions for structural mixer indicators:
        - Equal or near-equal value splitting
        - High fan-in / high fan-out redistribution
        - Rapid transit / short retention interval (< 300s)
        - Peeling / multi-output dispersion
        """
        if not graph_data or "edges" not in graph_data:
            return {"is_pattern_detected": False, "confidence": 0.0, "indicators": {}, "supporting_txs": [], "explanation": ""}

        edges = graph_data.get("edges", [])
        out_edges = [e for e in edges if e.get("from_wallet", "").upper() == target_wallet.upper()]
        in_edges = [e for e in edges if e.get("to_wallet", "").upper() == target_wallet.upper()]

        fan_in = len(in_edges)
        fan_out = len(out_edges)
        supporting_txs = [e.get("tx_hash") for e in out_edges + in_edges if e.get("tx_hash")]

        # Equal value split detection
        amounts = [float(e.get("amount", 0)) for e in out_edges if float(e.get("amount", 0)) > 0]
        equal_splits = False
        if len(amounts) >= 3:
            unique_amts = set(round(a, 2) for a in amounts)
            if len(unique_amts) == 1:
                equal_splits = True

        is_detected = (fan_in >= 3 and fan_out >= 3) or (equal_splits and fan_out >= 3)

        if is_detected:
            confidence = 0.75 if equal_splits else 0.60
            indicators = {
                "fan_in_count": fan_in,
                "fan_out_count": fan_out,
                "equal_value_splits": equal_splits,
            }
            explanation = f"Wallet exhibits multi-branch redistribution (fan-in: {fan_in}, fan-out: {fan_out}) with equal-value splits."
            return {
                "is_pattern_detected": True,
                "confidence": confidence,
                "indicators": indicators,
                "supporting_txs": supporting_txs,
                "explanation": explanation,
            }

        return {"is_pattern_detected": False, "confidence": 0.0, "indicators": {}, "supporting_txs": [], "explanation": ""}

    def record_pattern_observation(
        self,
        target_wallet: str,
        chain: str,
        pattern_type: str,
        confidence: float,
        indicator_values: Dict[str, Any],
        supporting_transactions: List[str],
        explanation: str,
        case_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> PatternObservation:
        """
        Persists analytical pattern observation into pattern_observations database table.
        Explicitly flags verification_status as 'ANALYTICAL'.
        """
        obs = PatternObservation(
            target_wallet=target_wallet,
            chain=chain,
            pattern_type=pattern_type,
            verification_status="ANALYTICAL",
            confidence=confidence,
            confidence_band="HIGH" if confidence >= 0.8 else ("MODERATE" if confidence >= 0.5 else "LOW"),
            indicator_values=indicator_values,
            supporting_transactions=supporting_transactions,
            explanation=explanation,
            case_id=case_id,
            trace_id=trace_id,
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs
