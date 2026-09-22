from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EvidenceChainStep(BaseModel):
    step_number: int
    element_type: str  # VASP | ENDPOINT_WALLET | ATTRIBUTION_SCORE | REASONING | SUPPORTING_TRANSACTION | EXPLORER_REFERENCE | VASP_PROVENANCE
    label: str
    value: str
    detail: str


class SahyogValidationResult(BaseModel):
    valid: bool
    status: str  # PACKAGE VALID | PACKAGE INVALID
    checked_at: str
    checked_fields: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class SahyogDisclosureRequestCreate(BaseModel):
    investigator_id: Optional[str] = Field(None, description="Investigator reference ID")
    reason_for_request: Optional[str] = Field("Authorized Law Enforcement Transaction Disclosure Request", description="Purpose of request")


class SahyogFreezeRequestCreate(BaseModel):
    investigator_id: Optional[str] = Field(None, description="Investigator reference ID")
    reason_for_request: Optional[str] = Field("Authorized Law Enforcement Asset Preservation / Freeze Request", description="Purpose of request")
    urgency_level: Optional[str] = Field("HIGH", description="Urgency classification")


class SahyogRequestResponse(BaseModel):
    request_id: str
    case_id: str
    job_id: Optional[str] = None
    request_type: str  # DISCLOSURE_REQUEST | ASSET_PRESERVATION_OR_FREEZE_REQUEST
    status: str  # DRAFT_REQUIRES_AUTHORISED_REVIEW
    package_version: str = "1.0"
    integration_status: str = "READY_FOR_AUTHORISED_API_INTEGRATION"
    target_wallet: str
    chain: str
    asset: str
    attributed_vasp: Optional[str] = None
    endpoint_address: Optional[str] = None
    attribution_score: float = 0.0
    confidence_level: str = "HIGH"
    hop_distance: int = 0
    endpoint_status: str = "TERMINAL ENDPOINT"
    validation_result: Optional[Dict[str, Any]] = None
    request_data: Dict[str, Any]
    evidence_chain: Optional[List[Dict[str, Any]]] = None
    evidence_snapshot_reference: Optional[str] = None
    exported_path: Optional[str] = None
    investigator_id: str = "INV-AUTOMATED-001"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SahyogStatusContractResponse(BaseModel):
    integration_status: str = "READY_FOR_AUTHORISED_API_INTEGRATION"
    generator_engine: str = "Specter High-Velocity Blockchain Intelligence Platform v1.0"
    contract_notice: str = "READY FOR AUTHORISED API INTEGRATION — NO LIVE UNLESS AUTHORISED"
    implemented_features: List[str] = Field(default_factory=list)
    ready_for_integration_features: List[str] = Field(default_factory=list)
    future_scope_features: List[str] = Field(default_factory=list)
