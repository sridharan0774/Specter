import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.vasp import VASPCluster, VASPRecord
from app.models.intelligence import CrossChainRelationship, PatternObservation
from app.intelligence.classifier import WalletRoleClassifier
from app.intelligence.mixer import MixerIntelligenceEngine
from app.intelligence.cross_chain import CrossChainIntelligenceEngine

logger = logging.getLogger("specter.api.intelligence")

router = APIRouter()


@router.get("/intelligence/entities/{address}", summary="Lookup Wallet Role & Intelligence Entity")
def get_entity_intelligence(
    address: str,
    chain: str = Query("TRON", description="Blockchain network"),
    db: Session = Depends(get_db),
):
    """
    Returns wallet classification, entity attribution, role taxonomy, verification status
    (VERIFIED, ANALYTICAL, UNKNOWN), confidence, and source provenance.
    """
    classifier = WalletRoleClassifier(db)
    result = classifier.classify_wallet(address=address, chain=chain)
    return result


@router.get("/intelligence/clusters/{cluster_id}", summary="Get VASP Wallet Cluster Details")
def get_vasp_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns VASP wallet cluster details connecting deposit, hot, operational, and cold storage wallets.
    """
    cluster = db.query(VASPCluster).filter(VASPCluster.cluster_id == cluster_id).first()
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VASP Wallet Cluster with ID '{cluster_id}' not found.",
        )
    return {
        "cluster_id": cluster.cluster_id,
        "vasp_name": cluster.vasp_name,
        "chain": cluster.chain,
        "cluster_type": cluster.cluster_type,
        "primary_wallet": cluster.primary_wallet,
        "member_wallets": cluster.member_wallets,
        "provenance": cluster.provenance,
        "source_quality_level": cluster.source_quality_level,
        "notes": cluster.notes,
        "created_at": cluster.created_at,
    }


@router.get("/intelligence/cross-chain/{case_id}", summary="Get Case Cross-Chain Relationships")
def get_case_cross_chain_relationships(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns list of cross-chain relationships, liquidity bridge transfers,
    and cross-chain service hops recorded for an investigation case.
    """
    engine = CrossChainIntelligenceEngine(db)
    relationships = engine.get_case_cross_chain_relationships(case_id)
    return relationships


@router.get("/intelligence/patterns/{case_id}", summary="Get Case Analytical Pattern Observations")
def get_case_pattern_observations(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns list of analytical pattern observations (e.g. Potential Mixer-Like Activity, Peeling) for a case.
    Strictly distinguishes ANALYTICAL indications from VERIFIED entity identities.
    """
    observations = (
        db.query(PatternObservation)
        .filter(PatternObservation.case_id == case_id)
        .order_by(PatternObservation.observed_at.desc())
        .all()
    )
    return observations
