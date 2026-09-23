import pytest
from sqlalchemy.orm import Session
from app.models.vasp import VASPCluster, VASPRecord
from app.models.intelligence import CrossChainRelationship, PatternObservation
from app.vasp.repository import VASPRepository
from app.intelligence.classifier import WalletRoleClassifier
from app.intelligence.mixer import MixerIntelligenceEngine
from app.intelligence.cross_chain import CrossChainIntelligenceEngine


def test_vasp_cluster_creation_and_membership(db: Session):
    repo = VASPRepository(db)
    repo.seed_known_public_vasps()

    clusters = db.query(VASPCluster).all()
    assert len(clusters) >= 2

    bybit_cluster = db.query(VASPCluster).filter(VASPCluster.cluster_id == "cluster-bybit-tron-01").first()
    assert bybit_cluster is not None
    assert bybit_cluster.vasp_name == "Bybit"
    assert len(bybit_cluster.member_wallets) >= 3

    # Check member wallet roles
    roles = [m.get("entity_role") for m in bybit_cluster.member_wallets]
    assert "HOT_WALLET" in roles
    assert "COLD_WALLET" in roles


def test_wallet_role_classification_verified_vs_unknown(db: Session):
    classifier = WalletRoleClassifier(db)

    # 1. Verified Cold Storage Wallet (Level 1 Official Binance)
    res_binance = classifier.classify_wallet("TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9", "TRON")
    assert res_binance["entity_name"] == "Binance"
    assert res_binance["verification_status"] == "VERIFIED"
    assert res_binance["confidence"] == 1.0

    # 2. Unknown Wallet (Never force identity)
    res_unknown = classifier.classify_wallet("TUnknownUnclassifiedAddress12345", "TRON")
    assert res_unknown["entity_name"] == "Unknown Entity"
    assert res_unknown["entity_role"] == "UNKNOWN"
    assert res_unknown["verification_status"] == "UNKNOWN"
    assert res_unknown["confidence"] == 0.0


def test_mixer_intelligence_verified_vs_analytical_pattern(db: Session):
    mixer_engine = MixerIntelligenceEngine(db)

    # Case A: Verified Mixer Entity
    res_verified = mixer_engine.evaluate_wallet_mixer_status("0xd90e2f925DA726b50C4Ed8D0Fb9091444027d323", "ETHEREUM")
    assert res_verified["verification_status"] == "VERIFIED"
    assert res_verified["label"] == "Verified Mixer / Tumbler"
    assert res_verified["entity_name"] == "Tornado Cash 100 ETH Router"

    # Case B: Analytical Pattern Indication (Equal-split outputs)
    graph_data = {
        "edges": [
            {"from_wallet": "TTestPatternWallet", "to_wallet": "TW1", "amount": 100.0, "tx_hash": "tx1"},
            {"from_wallet": "TTestPatternWallet", "to_wallet": "TW2", "amount": 100.0, "tx_hash": "tx2"},
            {"from_wallet": "TTestPatternWallet", "to_wallet": "TW3", "amount": 100.0, "tx_hash": "tx3"},
        ]
    }
    res_analytical = mixer_engine.evaluate_wallet_mixer_status("TTestPatternWallet", "TRON", graph_data)
    assert res_analytical["verification_status"] == "ANALYTICAL"
    assert res_analytical["label"] == "POTENTIAL MIXER-LIKE ACTIVITY"
    assert "CONFIRMED" not in res_analytical["label"]
    assert res_analytical["is_mixer_interaction"] is False  # Pattern indication, NOT verified mixer identity

    # Persist Pattern Observation
    obs = mixer_engine.record_pattern_observation(
        target_wallet="TTestPatternWallet",
        chain="TRON",
        pattern_type="POTENTIAL_MIXER_LIKE_ACTIVITY",
        confidence=0.75,
        indicator_values={"equal_split_amount": 100.0, "branch_count": 3},
        supporting_transactions=["tx1", "tx2", "tx3"],
        explanation="Equal value split redistribution across 3 branches",
    )
    assert obs.observation_id is not None
    assert obs.verification_status == "ANALYTICAL"


def test_bridge_and_cross_chain_relationships(db: Session):
    cross_engine = CrossChainIntelligenceEngine(db)

    # 1. Identify Verified Bridge Entity
    bridge_info = cross_engine.identify_bridge_or_service("0x609c690e8F7D68a59885c9132e812eEbDaAf0c9e", "ETHEREUM")
    assert bridge_info["is_cross_chain_entity"] is True
    assert bridge_info["entity_name"] == "Allbridge Core Router"
    assert bridge_info["entity_role"] == "BRIDGE"
    assert bridge_info["verification_status"] == "VERIFIED"


    # 2. Record Cross-Chain Relationship
    rel = cross_engine.record_cross_chain_relationship(
        source_chain="TRON",
        source_address="TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        source_tx_hash="tx_tron_01",
        service_entity="Allbridge Core Router",
        bridge_name="Allbridge",
        destination_chain="ETHEREUM",
        destination_address="0x1111111111111111111111111111111111111111",
        destination_tx_hash="tx_eth_01",
        relationship_type="BRIDGE_TRANSFER",
        asset_sent="USDT",
        amount_sent=5000.0,
        asset_received="USDT",
        amount_received=5000.0,
        provenance="Allbridge Official Contract Logs",
        case_id="case-test-cross-chain-01",
    )
    assert rel.relationship_id is not None
    assert rel.source_chain == "TRON"
    assert rel.destination_chain == "ETHEREUM"
    assert rel.relationship_type == "BRIDGE_TRANSFER"

    # Query relationships by case
    case_rels = cross_engine.get_case_cross_chain_relationships("case-test-cross-chain-01")
    assert len(case_rels) == 1
    assert case_rels[0].service_entity == "Allbridge Core Router"
