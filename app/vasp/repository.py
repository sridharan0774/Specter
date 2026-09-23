import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.vasp import VASPRecord

logger = logging.getLogger("specter.vasp.repository")


class VASPRepository:
    """
    Repository for managing known VASP and entity intelligence with source provenance.
    Distinguishes source quality levels (Level 1 Official to Level 5 Unverified).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_address(self, address: str, chain: str = "TRON") -> Optional[VASPRecord]:
        """Lookup entity record by exact address and chain."""
        if not address:
            return None
        return (
            self.db.query(VASPRecord)
            .filter(
                VASPRecord.address.classmethod == address.strip() if hasattr(VASPRecord.address, 'classmethod') else VASPRecord.address == address.strip(),
                VASPRecord.chain == chain.upper().strip(),
            )
            .first()
        )

    def search_entity(self, address: str, chain: Optional[str] = None) -> Optional[VASPRecord]:
        """Case-insensitive exact address lookup across intelligence records."""
        if not address:
            return None
        clean_addr = address.strip().upper()
        query = self.db.query(VASPRecord)
        if chain:
            query = query.filter(VASPRecord.chain == chain.upper().strip())
        records = query.all()
        for r in records:
            if r.address.strip().upper() == clean_addr:
                return r
        # Fallback: Search across all chains if chain filter produced no match
        all_records = self.db.query(VASPRecord).all()
        for r in all_records:
            if r.address.strip().upper() == clean_addr:
                return r
        return None


    def get_attributable_vasps(self, chain: str = "TRON") -> List[VASPRecord]:
        """Return all entity intelligence records eligible for VASP attribution (excludes token contracts/issuers)."""
        records = self.db.query(VASPRecord).filter(VASPRecord.chain == chain.upper().strip()).all()
        return [r for r in records if r.is_attributable_vasp]

    def add_intelligence_record(
        self,
        address: str,
        chain: str,
        entity_name: str,
        entity_type: str,
        label_type: str,
        source: str,
        source_url: Optional[str] = None,
        source_reference: Optional[str] = None,
        source_quality_level: int = 3,
        confidence: float = 1.0,
        notes: Optional[str] = None,
        entity_role: Optional[str] = None,
    ) -> VASPRecord:
        """Add verified entity intelligence record into repository with provenance."""
        # Determine strict role classification: VASP, TOKEN_ISSUER, TOKEN_CONTRACT, INFRASTRUCTURE
        clean_addr = address.strip().upper()
        if clean_addr == "TR7NHQJEKXGTCI8Q8ZY4PL8OTSZGJLJ6T":
            eff_role = "TOKEN_CONTRACT"
        elif entity_role:
            eff_role = entity_role.upper().strip()
        elif entity_type.upper().strip() in ("TOKEN_CONTRACT", "CONTRACT"):
            eff_role = "TOKEN_CONTRACT"
        elif entity_type.upper().strip() in ("TOKEN_ISSUER", "ISSUER", "ISSUER_CUSTODIAL"):
            eff_role = "TOKEN_ISSUER"
        elif entity_type.upper().strip() in ("INFRASTRUCTURE", "BRIDGE", "MIXER", "DEFI"):
            eff_role = "INFRASTRUCTURE"
        else:
            eff_role = "VASP"

        record = VASPRecord(
            address=address.strip(),
            chain=chain.upper().strip(),
            entity_name=entity_name.strip(),
            entity_role=eff_role,
            entity_type=entity_type.upper().strip(),
            label_type=label_type.lower().strip(),
            source=source.strip(),
            source_url=source_url,
            source_reference=source_reference,
            source_quality_level=max(1, min(5, source_quality_level)),
            confidence=max(0.0, min(1.0, confidence)),
            verified_at=datetime.now(timezone.utc),
            notes=notes,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def seed_known_public_vasps(self) -> int:
        """
        Seed and synchronize database with verified, evidence-backed VASP and entity intelligence.
        Purges legacy placeholder and unverified seeds (e.g. TND9w8n..., synthetic seeds, mislabeled tokens).
        Preserves non-VASP infrastructure entities (Tether Treasury, USDT Contract) with strict non-VASP roles.
        """
        # Explicit blocklist of legacy placeholder or unsupported addresses to purge from existing databases
        discarded_addresses = [
            "TND9w8n8n8n8n8n8n8n8n8n8n8n8n8n8n8",  # Placeholder synthetic string with repeating n8, invalid on TRON
            "TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn",  # Mislabeled USDD Token Contract on TRON, not a VASP
            "TJCnKsPa7y5okkXvQWBzxaZ2MJK7JBFZ12",  # Fake/synthetic address, invalid on TRON
            "TAqDQCKgQozPRd9GPASCPQHYMx7Yt1LbAv",  # Unverified address without public explorer or official backing
            "TQn9Y2khEsLJW1ChVWFMSMeSTow5KcbqSE",  # Fake/synthetic address, invalid on TRON
            "TKHuVq1oebufufatmBwvu18y8R5Jw2n2Vb",  # Fake/synthetic address, invalid on TRON
            "0x1000000000000000000000000000000000000001",  # Legacy synthetic Allbridge address placeholder
            "0xChangeNOW111111111111111111111111111111",  # Legacy synthetic ChangeNOW address placeholder
        ]

        # 1. Purge unsupported legacy seeds from the existing database
        all_existing = self.db.query(VASPRecord).all()
        for discarded in discarded_addresses:
            for m in all_existing:
                if m.address.strip().upper() == discarded.strip().upper():
                    logger.info(f"Purging unverified legacy seed record: {m.address} ({m.entity_name})")
                    self.db.delete(m)
        self.db.commit()

        # 2. Verified, evidence-based intelligence records
        public_seeds = [
            # Non-VASP: Token Issuer (Level 1 Official)
            {
                "address": "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
                "chain": "TRON",
                "entity_name": "Tether Treasury",
                "entity_role": "TOKEN_ISSUER",
                "entity_type": "TOKEN_ISSUER",
                "label_type": "treasury_address",
                "source": "TronScan Official Explorer",
                "source_url": "https://tronscan.org/#/address/TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
                "source_reference": "TS-OFFICIAL-TR7NH-TREASURY",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Official Tether TRC20 Treasury & Mint Address on TRON mainnet. Excluded from VASP attribution.",
            },
            # Non-VASP: Token Contract (Level 1 Official)
            {
                "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "chain": "TRON",
                "entity_name": "Tether USDT Contract",
                "entity_role": "TOKEN_CONTRACT",
                "entity_type": "TOKEN_CONTRACT",
                "label_type": "contract_address",
                "source": "Tether Official Whitepaper & TronScan",
                "source_url": "https://tronscan.org/#/token20/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                "source_reference": "TETHER-TRC20-OFFICIAL",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Official TRC20 USDT Smart Contract on TRON. Not an exchange or VASP endpoint. Excluded from VASP attribution.",
            },
            # Verified Binance: Level 1 Official Proof of Reserves
            {
                "address": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
                "chain": "TRON",
                "entity_name": "Binance",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "cold_wallet",
                "source": "Binance Official Proof of Reserves & Transparency Report",
                "source_url": "https://www.binance.com/en/blog/community/our-commitment-to-transparency-2895840147147652626",
                "source_reference": "BINANCE-POR-TRON-COLD-01",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Official Binance TRC20 cold storage and reserve wallet holding over 7B USDT.",
            },
            {
                "address": "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb",
                "chain": "TRON",
                "entity_name": "Binance",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "cold_wallet",
                "source": "Binance Official Proof of Reserves & Transparency Report",
                "source_url": "https://www.binance.com/en/blog/community/our-commitment-to-transparency-2895840147147652626",
                "source_reference": "BINANCE-POR-TRON-COLD-02",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Official Binance TRC20 reserve wallet published in Binance transparency report holding over 5.7B USDT.",
            },
            {
                "address": "TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuSi",
                "chain": "TRON",
                "entity_name": "Binance",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "cold_wallet",
                "source": "Binance Official Proof of Reserves & Transparency Report",
                "source_url": "https://www.binance.com/en/blog/community/our-commitment-to-transparency-2895840147147652626",
                "source_reference": "BINANCE-POR-TRON-COLD-03",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Official Binance TRC20 reserve wallet published in Binance transparency report holding over 1.5B USDT.",
            },
            # Verified OKX: Level 2 TRONSCAN Authoritative Public Explorer Label
            {
                "address": "TLaGjwhvA8XQYSxFAcAXy7Dvuue9eGYitv",
                "chain": "TRON",
                "entity_name": "OKX",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "hot_wallet",
                "source": "TRONSCAN Public Entity Labels",
                "source_url": "https://tronscan.org/#/address/TLaGjwhvA8XQYSxFAcAXy7Dvuue9eGYitv",
                "source_reference": "TRONSCAN-LABEL-OKX-HOT-08",
                "source_quality_level": 2,
                "confidence": 0.98,
                "notes": "Publicly tagged on TRONSCAN as OKX Hot Wallet 8, active exchange operational settlement wallet.",
            },
            # Verified Kraken: Level 2 TRONSCAN Authoritative Public Explorer Label
            {
                "address": "TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76",
                "chain": "TRON",
                "entity_name": "Kraken",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "hot_wallet",
                "source": "TRONSCAN Public Entity Labels",
                "source_url": "https://tronscan.org/#/address/TG2CMGxnTPgQ6V58kiKd7wbyN8ewtAmY76",
                "source_reference": "TRONSCAN-LABEL-KRAKEN-HOT-01",
                "source_quality_level": 2,
                "confidence": 0.98,
                "notes": "Publicly tagged on TRONSCAN as Kraken: Hot Wallet, handling TRC20 USDT flow and customer withdrawals.",
            },
            # Verified Bybit: Level 1 Official Exchange Documentation & Proof of Reserves
            {
                "address": "TTH75Z9rfRgzCLNDDYBaR2WjUvuSDRtSMg",
                "chain": "TRON",
                "entity_name": "Bybit",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "cold_wallet",
                "source": "Bybit Official Wallet Address Ownership Documentation & PoR Audit",
                "source_url": "https://www.bybit.com/en/proof-of-reserves/",
                "source_reference": "BYBIT-OFFICIAL-OWNERSHIP-TRON-01",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Officially published in Bybit Proof of Reserves audits and wallet ownership documentation for TRON USDT.",
            },
            {
                "address": "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY",
                "chain": "TRON",
                "entity_name": "Bybit",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "hot_wallet",
                "source": "Bybit Official Wallet Address Ownership Documentation",
                "source_url": "https://www.bybit.com/en/help-center/s/article/Bybit-Wallet-Addresses-Ownership-Explained",
                "source_reference": "BYBIT-OFFICIAL-OWNERSHIP-TRON-02",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Officially published in Bybit wallet address ownership transparency list for TRON TRC20 USDT.",
            },
            {
                "address": "TXRRpT4BZ3dB5ShUQew2HXv1iK3Gg4MM9j",
                "chain": "TRON",
                "entity_name": "Bybit",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "hot_wallet",
                "source": "Bybit Official Wallet Address Ownership Documentation",
                "source_url": "https://www.bybit.com/en/help-center/s/article/Bybit-Wallet-Addresses-Ownership-Explained",
                "source_reference": "BYBIT-OFFICIAL-OWNERSHIP-TRON-03",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Officially published in Bybit wallet address ownership transparency documentation for TRON USDT.",
            },
            {
                "address": "TB1WQmj63bHV9Qmuhp39WABzutphMAetSc",
                "chain": "TRON",
                "entity_name": "Bybit",
                "entity_role": "VASP",
                "entity_type": "EXCHANGE",
                "label_type": "cold_wallet",
                "source": "Bybit Official Wallet Address Ownership Documentation & PoR Audit",
                "source_url": "https://www.bybit.com/en/proof-of-reserves/",
                "source_reference": "BYBIT-OFFICIAL-OWNERSHIP-TRON-04",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Officially published in Bybit Proof of Reserves audits and wallet ownership documentation for TRON USDT.",
            },
            # Verified Mixer Entity (Level 1 Official Advisory)
            {
                "address": "0xd90e2f925DA726b50C4Ed8D0Fb9091444027d323",
                "chain": "ETHEREUM",
                "entity_name": "Tornado Cash 100 ETH Router",
                "entity_role": "MIXER",
                "entity_type": "MIXER",
                "label_type": "mixer_contract",
                "source": "OFAC Sanctions List & Etherscan Official Tag",
                "source_url": "https://etherscan.io/address/0xd90e2f925DA726b50C4Ed8D0Fb9091444027d323",
                "source_reference": "OFAC-SDN-TORNADO-100ETH",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Verified non-custodial privacy mixer router contract on Ethereum. Classified as MIXER.",
            },
            # Verified Bridge Entity (Level 1 Official)
            {
                "address": "0x609c690e8F7D68a59885c9132e812eEbDaAf0c9e",
                "chain": "ETHEREUM",
                "entity_name": "Allbridge Core Router",
                "entity_role": "BRIDGE",
                "entity_type": "BRIDGE",
                "label_type": "bridge_contract",
                "source": "Allbridge Official Documentation & Contract Registry",
                "source_url": "https://docs-core.allbridge.io/product/how-does-allbridge-core-work/allbridge-core-contracts",
                "source_reference": "ALLBRIDGE-CORE-ETH-ROUTER",
                "source_quality_level": 1,
                "confidence": 1.0,
                "notes": "Verified cross-chain liquidity bridge router connecting EVM and TRON chains. Classified as BRIDGE. Not an attributable VASP.",
            },
        ]

        added_or_updated_count = 0
        for seed in public_seeds:
            existing = self.search_entity(seed["address"], seed["chain"])
            if not existing:
                self.add_intelligence_record(**seed)
                added_or_updated_count += 1
            else:
                updated = False
                for field, val in seed.items():
                    if hasattr(existing, field) and getattr(existing, field) != val:
                        setattr(existing, field, val)
                        updated = True
                if updated:
                    self.db.commit()
                    added_or_updated_count += 1

        # Seed VASP Clusters
        self.seed_vasp_clusters()

        return added_or_updated_count

    def seed_vasp_clusters(self) -> None:
        """Seed verified VASP Wallet Clusters connecting deposit, hot, and cold storage wallets."""
        from app.models.vasp import VASPCluster

        clusters_data = [
            {
                "cluster_id": "cluster-binance-tron-01",
                "vasp_name": "Binance",
                "chain": "TRON",
                "cluster_type": "EXCHANGE_CLUSTER",
                "primary_wallet": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
                "member_wallets": [
                    {"address": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9", "entity_role": "COLD_WALLET", "label_type": "cold_storage"},
                    {"address": "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb", "entity_role": "COLD_WALLET", "label_type": "cold_storage"},
                    {"address": "TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuSi", "entity_role": "COLD_WALLET", "label_type": "cold_storage"},
                ],
                "provenance": "Binance Official Proof of Reserves Transparency Audit",
                "source_quality_level": 1,
                "notes": "Verified Binance TRON USDT cluster holding official reserve wallets.",
            },
            {
                "cluster_id": "cluster-bybit-tron-01",
                "vasp_name": "Bybit",
                "chain": "TRON",
                "cluster_type": "EXCHANGE_CLUSTER",
                "primary_wallet": "TTH75Z9rfRgzCLNDDYBaR2WjUvuSDRtSMg",
                "member_wallets": [
                    {"address": "TTH75Z9rfRgzCLNDDYBaR2WjUvuSDRtSMg", "entity_role": "COLD_WALLET", "label_type": "cold_storage"},
                    {"address": "TBpr1tQ5kvoKMv85XsCESVavYo4oZZdWpY", "entity_role": "HOT_WALLET", "label_type": "hot_wallet"},
                    {"address": "TXRRpT4BZ3dB5ShUQew2HXv1iK3Gg4MM9j", "entity_role": "HOT_WALLET", "label_type": "hot_wallet"},
                    {"address": "TB1WQmj63bHV9Qmuhp39WABzutphMAetSc", "entity_role": "COLD_WALLET", "label_type": "cold_storage"},
                ],
                "provenance": "Bybit Official Wallet Ownership Transparency List",
                "source_quality_level": 1,
                "notes": "Verified Bybit TRON USDT exchange cluster holding hot and cold storage wallets.",
            },
        ]

        for c_data in clusters_data:
            existing = self.db.query(VASPCluster).filter(VASPCluster.cluster_id == c_data["cluster_id"]).first()
            if not existing:
                cluster_rec = VASPCluster(**c_data)
                self.db.add(cluster_rec)
        self.db.commit()

