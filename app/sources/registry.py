from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_id: str
    name: str
    source_type: str  # BLOCKCHAIN_L1_RPC, VASP_INTELLIGENCE_DB, ANALYTICAL_ENGINE, OFFICIAL_REGISTRY
    quality_tier: int = Field(1, description="1 (High - On-chain/Official), 2 (Medium - Verified), 3 (Low - Heuristic)")
    default_confidence: float = Field(0.9, ge=0.0, le=1.0)
    uri_base: Optional[str] = None
    description: str
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceRegistry:
    """
    Registry for source attribution and verification tracking across Specter investigation artifacts.
    """

    def __init__(self):
        self._sources: Dict[str, SourceMetadata] = {}
        self._initialize_default_sources()

    def _initialize_default_sources(self):
        default_sources = [
            SourceMetadata(
                source_id="SRC_TRON_RPC",
                name="TRON Network RPC Node",
                source_type="BLOCKCHAIN_L1_RPC",
                quality_tier=1,
                default_confidence=1.0,
                uri_base="https://tronscan.org/#/transaction/",
                description="Direct TRON Layer-1 blockchain ledger state and transaction data.",
            ),
            SourceMetadata(
                source_id="SRC_SPECTER_VASP_DB",
                name="Specter VASP Intelligence Database",
                source_type="VASP_INTELLIGENCE_DB",
                quality_tier=1,
                default_confidence=0.95,
                uri_base=None,
                description="Verified directory of Virtual Asset Service Providers, exchange hot wallets, and deposit addresses.",
            ),
            SourceMetadata(
                source_id="SRC_SPECTER_VELOCITY_ENGINE",
                name="Specter High-Velocity Movement Engine v1.0",
                source_type="ANALYTICAL_ENGINE",
                quality_tier=1,
                default_confidence=0.90,
                uri_base=None,
                description="Automated rolling-window velocity and delta_t structural analysis engine.",
            ),
            SourceMetadata(
                source_id="SRC_SPECTER_TYPOLOGY_ENGINE",
                name="Specter Transaction Typology Engine v1.0",
                source_type="ANALYTICAL_ENGINE",
                quality_tier=1,
                default_confidence=0.90,
                uri_base=None,
                description="Graph pattern analysis engine for Fan-Out, Fan-In, Consolidation, and Rapid Peel-Like movements.",
            ),
            SourceMetadata(
                source_id="SRC_SPECTER_RISK_ENGINE",
                name="Specter Risk Intelligence Engine v1.0",
                source_type="ANALYTICAL_ENGINE",
                quality_tier=1,
                default_confidence=0.90,
                uri_base=None,
                description="Composite Transaction-Flow Risk Indicator calculation engine with contextual safety mitigations.",
            ),
            SourceMetadata(
                source_id="SRC_OFFICIAL_REGISTRY",
                name="Official FIU/Corporate Entity Registry",
                source_type="OFFICIAL_REGISTRY",
                quality_tier=1,
                default_confidence=0.98,
                uri_base=None,
                description="Official law enforcement and regulatory registry data.",
            ),
        ]
        for src in default_sources:
            self._sources[src.source_id] = src

    def register_source(self, metadata: SourceMetadata) -> None:
        self._sources[metadata.source_id] = metadata

    def get_source(self, source_id: str) -> Optional[SourceMetadata]:
        return self._sources.get(source_id)

    def list_sources(self) -> List[SourceMetadata]:
        return list(self._sources.values())


# Global singleton instance
source_registry = SourceRegistry()
