import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.intelligence import CrossChainRelationship
from app.intelligence.classifier import WalletRoleClassifier

logger = logging.getLogger("specter.intelligence.cross_chain")


class CrossChainIntelligenceEngine:
    """
    Bridge & Cross-Chain Service Intelligence Engine.
    Detects, links, and manages cross-chain fund flows, liquidity bridge transfers,
    and cross-chain swap relationships while preserving chain boundaries.
    """

    def __init__(self, db: Session):
        self.db = db
        self.classifier = WalletRoleClassifier(db)

    def identify_bridge_or_service(self, address: str, chain: str) -> Dict[str, Any]:
        """
        Identifies whether an address belongs to a verified Bridge or Cross-Chain Service.
        """
        cls_info = self.classifier.classify_wallet(address, chain)
        role = cls_info["entity_role"]

        if role in ["BRIDGE", "CROSS_CHAIN_SERVICE"]:
            return {
                "address": address,
                "chain": chain,
                "is_cross_chain_entity": True,
                "entity_name": cls_info["entity_name"],
                "entity_role": role,
                "verification_status": "VERIFIED",
                "confidence": cls_info["confidence"],
                "source": cls_info["source_name"],
                "source_url": cls_info["source_url"],
                "evidence_summary": [
                    f"✓ Verified {role} entity '{cls_info['entity_name']}' matched in intelligence database",
                    f"✓ Provenance: {cls_info['source_name']}",
                ],
            }

        return {
            "address": address,
            "chain": chain,
            "is_cross_chain_entity": False,
            "entity_name": "Unknown Entity",
            "entity_role": "UNKNOWN",
            "verification_status": "UNKNOWN",
            "confidence": 0.0,
            "source": "SPECTER Engine",
            "source_url": None,
            "evidence_summary": ["• No verified bridge or cross-chain service relationship identified."],
        }

    def record_cross_chain_relationship(
        self,
        source_chain: str,
        source_address: str,
        source_tx_hash: str,
        service_entity: str,
        destination_chain: str,
        destination_address: str,
        destination_tx_hash: Optional[str] = None,
        relationship_type: str = "BRIDGE_TRANSFER",
        bridge_name: Optional[str] = None,
        asset_sent: Optional[str] = None,
        amount_sent: Optional[float] = None,
        asset_received: Optional[str] = None,
        amount_received: Optional[float] = None,
        provenance: str = "SPECTER Cross-Chain Graph Engine",
        case_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> CrossChainRelationship:
        """
        Persists verified or analytical cross-chain fund flow relationship.
        Differentiates BRIDGE_TRANSFER, CROSS_CHAIN_SWAP, SERVICE_TRANSFER, and UNKNOWN.
        """
        rel = CrossChainRelationship(
            case_id=case_id,
            source_chain=source_chain.upper().strip(),
            source_address=source_address.strip(),
            source_tx_hash=source_tx_hash.strip(),
            service_entity=service_entity.strip(),
            bridge_name=bridge_name,
            destination_chain=destination_chain.upper().strip(),
            destination_address=destination_address.strip(),
            destination_tx_hash=destination_tx_hash.strip() if destination_tx_hash else None,
            relationship_type=relationship_type.upper().strip(),
            verification_status="VERIFIED" if service_entity != "UNKNOWN_CROSS_CHAIN_SERVICE" else "ANALYTICAL",
            confidence=1.0 if service_entity != "UNKNOWN_CROSS_CHAIN_SERVICE" else 0.5,
            asset_sent=asset_sent,
            amount_sent=amount_sent,
            asset_received=asset_received,
            amount_received=amount_received,
            evidence_summary=[
                f"✓ Cross-chain relationship: {source_chain} ({source_address[:8]}...) → {service_entity} → {destination_chain} ({destination_address[:8]}...)",
                f"✓ Relationship type: {relationship_type}",
            ],
            provenance=provenance,
            notes=notes,
        )
        self.db.add(rel)
        self.db.commit()
        self.db.refresh(rel)
        return rel

    def get_case_cross_chain_relationships(self, case_id: str) -> List[CrossChainRelationship]:
        """Returns all cross-chain relationships recorded for a specific case ID."""
        return (
            self.db.query(CrossChainRelationship)
            .filter(CrossChainRelationship.case_id == case_id)
            .order_by(CrossChainRelationship.created_at.desc())
            .all()
        )
