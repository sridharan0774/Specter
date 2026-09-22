import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.vasp import VASPRecord, VASPCluster
from app.vasp.repository import VASPRepository

logger = logging.getLogger("specter.intelligence.classifier")


class WalletRoleClassifier:
    """
    Role Classification Engine for Blockchain Wallets.
    Distinguishes:
    - VERIFIED: Explicit intelligence label from authoritative source
    - ANALYTICAL: Derived structural heuristic indicator
    - UNKNOWN: Insufficient evidence
    """

    def __init__(self, db: Session):
        self.db = db
        self.vasp_repo = VASPRepository(db)
        self.vasp_repo.seed_known_public_vasps()


    def classify_wallet(self, address: str, chain: str = "TRON") -> Dict[str, Any]:
        """
        Classifies wallet address role, entity parent, cluster membership,
        verification status, confidence score, and source provenance.
        """
        if not address:
            return self._unknown_classification(address, chain)

        clean_addr = address.strip()
        chain_upper = chain.upper().strip()

        # 1. Check exact VASPRecord database intelligence
        record = self.vasp_repo.search_entity(clean_addr, chain_upper)
        if record:
            return {
                "address": clean_addr,
                "chain": chain_upper,
                "entity_name": record.entity_name,
                "entity_role": record.entity_role,
                "entity_type": record.entity_type,
                "label_type": record.label_type,
                "verification_status": "VERIFIED",
                "confidence": record.confidence,
                "source_type": "OFFICIAL" if record.source_quality_level == 1 else "BLOCKCHAIN_EXPLORER",
                "source_name": record.source,
                "source_url": record.source_url,
                "source_reference": record.source_reference,
                "notes": record.notes,
                "is_attributable_vasp": record.is_attributable_vasp,
                "evidence_summary": [
                    f"✓ Entity identified as '{record.entity_name}' via verified intelligence",
                    f"✓ Explicit role classification: {record.entity_role}",
                    f"✓ Provenance: {record.source} (Level {record.source_quality_level})"
                ],
            }

        # 2. Check VASPCluster membership
        clusters = self.db.query(VASPCluster).filter(VASPCluster.chain == chain_upper).all()
        for cluster in clusters:
            members = cluster.member_wallets or []
            for member in members:
                if member.get("address", "").strip().upper() == clean_addr.upper():
                    role = member.get("entity_role", "DIRECT_DEPOSIT_WALLET")
                    return {
                        "address": clean_addr,
                        "chain": chain_upper,
                        "entity_name": cluster.vasp_name,
                        "entity_role": role,
                        "entity_type": "EXCHANGE",
                        "label_type": member.get("label_type", "cluster_member"),
                        "cluster_id": cluster.cluster_id,
                        "verification_status": "VERIFIED",
                        "confidence": 1.0,
                        "source_type": "OFFICIAL",
                        "source_name": cluster.provenance,
                        "source_url": None,
                        "notes": f"Member wallet of {cluster.vasp_name} cluster ({cluster.cluster_id})",
                        "is_attributable_vasp": True,
                        "evidence_summary": [
                            f"✓ Wallet verified as member of '{cluster.vasp_name}' cluster ({cluster.cluster_id})",
                            f"✓ Cluster role: {role}",
                            f"✓ Cluster Provenance: {cluster.provenance}"
                        ],
                    }

        # 3. Fallback: Return UNKNOWN classification (never invent identities)
        return self._unknown_classification(clean_addr, chain_upper)

    def _unknown_classification(self, address: str, chain: str) -> Dict[str, Any]:
        return {
            "address": address,
            "chain": chain,
            "entity_name": "Unknown Entity",
            "entity_role": "UNKNOWN",
            "entity_type": "UNKNOWN",
            "label_type": "unclassified_wallet",
            "verification_status": "UNKNOWN",
            "confidence": 0.0,
            "source_type": "INTERNAL_ANALYSIS",
            "source_name": "SPECTER Analytical Engine",
            "source_url": None,
            "notes": "Insufficient intelligence to attribute explicit entity identity.",
            "is_attributable_vasp": False,
            "evidence_summary": [
                "• Unclassified blockchain wallet",
                "• Insufficient intelligence for entity attribution"
            ],
        }
