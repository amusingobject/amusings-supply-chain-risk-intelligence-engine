"""Canonical records for contract v0.1.

Strict Pydantic models, closed controlled enumerations, RFC 3339 UTC timestamps,
deterministic traceability, and human-in-the-loop authorization gates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rock_supply_intelligence.schemas.common import (
    SHA256_RE,
    ActionType,
    ApprovalState,
    CanonicalRef,
    CarrierEventType,
    EventState,
    EventType,
    ExposureStatus,
    ExposureType,
    ExtractionMethod,
    InventoryRisk,
    LinkageMethod,
    Mode,
    ObservedOrInferred,
    POStatus,
    Priority,
    RecommendationStatus,
    RecordStatus,
    SCHEMA_VERSION,
    Severity,
    SharedRecord,
    ShipmentStatus,
    SourceType,
    SubjectType,
    SupplierStatus,
    TENANT_POC,
    validate_iso6346_checksum,
    validate_rfc3339_or_date,
    validate_rfc3339_source,
    validate_rfc3339_utc,
)
from rock_supply_intelligence.schemas.source_quality import SourceQuality


class ExtractionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: ExtractionMethod
    model_or_rule: str | None = None
    prompt_version: str | None = None
    execution_class: Literal["local", "cloud", "human", "deterministic", "pending"] | None = None
    reviewer: str | None = None


class Evidence(SharedRecord):
    """Append-only observation record. Material claims must cite Evidence IDs."""

    source_name: str
    source_type: SourceType
    source_locator: str
    publisher: str | None = None
    source_authority: str | None = None
    retrieved_at: str
    published_at: str | None = None
    observed_at: str | None = None
    effective_at: str | None = None
    content_hash: str | None = None
    hash_method: Literal["sha256"] | None = "sha256"
    raw_ref: str
    excerpt_or_payload_path: str
    license: str | None = None
    access_constraints: str | None = None
    language: str | None = None
    synthetic: bool = False
    extraction: ExtractionTrace
    source_quality: SourceQuality | None = None
    supersedes: str | None = None
    retracts: str | None = None

    @field_validator("retrieved_at", mode="after")
    @classmethod
    def _validate_retrieved_at(cls, v: str) -> str:
        res = validate_rfc3339_utc(v)
        if res is None:
            raise ValueError("retrieved_at is required")
        return res

    @field_validator("published_at", "observed_at", "effective_at", mode="after")
    @classmethod
    def _validate_source_timestamps(cls, v: str | None) -> str | None:
        return validate_rfc3339_source(v)

    @field_validator("content_hash", mode="after")
    @classmethod
    def _validate_content_hash(cls, v: str | None) -> str | None:
        if v is not None and not SHA256_RE.match(v):
            raise ValueError(f"content_hash {v!r} must be a 64-character lowercase hex SHA-256 string")
        return v

    @model_validator(mode="after")
    def _validate_evidence_invariants(self) -> Evidence:
        if self.status in {"active", "archived"}:
            if self.content_hash is None and not self.raw_ref.endswith("/"):
                raise ValueError("active evidence with a file raw_ref requires content_hash")
            if self.source_name == "TO_BE_COLLECTED":
                raise ValueError("active evidence cannot have placeholder source_name 'TO_BE_COLLECTED'")
            if self.excerpt_or_payload_path == "TO_BE_COLLECTED":
                raise ValueError("active evidence cannot have placeholder excerpt_or_payload_path 'TO_BE_COLLECTED'")
        return self


class ExternalEvent(SharedRecord):
    """External disruption signal normalized to canonical types."""

    event_type: EventType
    event_state: EventState
    title: str
    start_time: str | None = None
    end_time: str | None = None
    geometry: dict | None = None
    locations: list[CanonicalRef] = Field(default_factory=list)
    entities: list[CanonicalRef] = Field(default_factory=list)
    severity: Severity
    source_event_ids: list[str] = Field(default_factory=list)
    observed_or_inferred: ObservedOrInferred
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_severity: str | None = None

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _validate_event_times(cls, v: str | None) -> str | None:
        return validate_rfc3339_utc(v)

    @model_validator(mode="after")
    def _validate_event_invariants(self) -> ExternalEvent:
        if not self.evidence_ids:
            raise ValueError("ExternalEvent requires at least one evidence_id")
        if self.start_time and self.end_time:
            if self.start_time > self.end_time:
                raise ValueError(f"start_time ({self.start_time}) cannot be after end_time ({self.end_time})")
        return self


class PurchaseOrderLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: str
    quantity_ordered: float = Field(gt=0)
    unit_cost: float | None = Field(default=None, ge=0)
    promised_date: str | None = None
    received_quantity: float | None = Field(default=None, ge=0)

    @field_validator("promised_date", mode="after")
    @classmethod
    def _validate_promised_date(cls, v: str | None) -> str | None:
        return validate_rfc3339_or_date(v)


class PurchaseOrder(SharedRecord):
    po_number: str
    supplier_id: str
    order_date: str | None = None
    po_status: POStatus = "open"
    currency: str = "USD"
    lines: list[PurchaseOrderLine]
    ship_to_location_id: str | None = None
    incoterm: str | None = None

    @field_validator("order_date", mode="after")
    @classmethod
    def _validate_order_date(cls, v: str | None) -> str | None:
        return validate_rfc3339_or_date(v)

    @model_validator(mode="after")
    def _validate_po_invariants(self) -> PurchaseOrder:
        if not self.lines:
            raise ValueError("PurchaseOrder must have at least one line")
        return self


class ShipmentLeg(BaseModel):
    """A discrete leg of freight transit. 1-based and immutable within shipment."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    tenant_id: str = TENANT_POC
    created_at: str | None = None
    updated_at: str | None = None
    leg_sequence: int = Field(ge=1)
    mode: Mode
    origin: str
    destination: str
    origin_locode: str | None = None
    destination_locode: str | None = None
    planned_departure: str | None = None
    planned_arrival: str | None = None
    actual_departure: str | None = None
    actual_arrival: str | None = None
    status: ShipmentStatus
    carrier_id: str | None = None
    vessel_or_flight_ref: str | None = None
    route_geometry: dict | None = None
    handoff_location: str | None = None
    transit_baseline: dict | None = None
    related_events: list[str] = Field(default_factory=list)

    @field_validator(
        "created_at",
        "updated_at",
        "planned_departure",
        "planned_arrival",
        "actual_departure",
        "actual_arrival",
        mode="after",
    )
    @classmethod
    def _validate_leg_timestamps(cls, v: str | None) -> str | None:
        return validate_rfc3339_utc(v)


class Shipment(SharedRecord):
    shipment_number: str
    shipment_status: ShipmentStatus = "booked"
    mode: Mode = "ocean"
    origin: str
    destination: str
    origin_locode: str | None = None
    destination_locode: str | None = None
    planned_departure: str | None = None
    planned_arrival: str | None = None
    actual_departure: str | None = None
    actual_arrival: str | None = None
    carrier_id: str | None = None
    booking_ref: str | None = None
    bill_of_lading: str | None = None
    po_refs: list[str] = Field(default_factory=list)
    container_refs: list[str] = Field(default_factory=list)
    legs: list[ShipmentLeg] = Field(default_factory=list)

    @field_validator(
        "planned_departure",
        "planned_arrival",
        "actual_departure",
        "actual_arrival",
        mode="after",
    )
    @classmethod
    def _validate_shipment_timestamps(cls, v: str | None) -> str | None:
        return validate_rfc3339_utc(v)

    @model_validator(mode="after")
    def _validate_legs_order(self) -> Shipment:
        if self.legs:
            sequences = [leg.leg_sequence for leg in self.legs]
            if len(set(sequences)) != len(sequences):
                raise ValueError("Shipment leg sequences must be unique")
            if any(s < 1 for s in sequences):
                raise ValueError("Shipment leg sequence must be >= 1")
        return self


class Container(SharedRecord):
    container_number: str
    container_type: str | None = None
    container_status: str = "active"
    shipment_id: str | None = None
    seal: str | None = None
    owner: str | None = None
    gross_weight: float | None = None
    last_known_position: str | None = None
    tracking_events: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_container_number(self) -> Container:
        # Check standard ISO 6346 check digit where format allows
        s = self.container_number.strip().upper()
        if len(s) == 11 and s[:4].isalpha() and s[4:].isdigit():
            if not validate_iso6346_checksum(s):
                raise ValueError(
                    f"Container number {self.container_number!r} failed ISO 6346 check digit validation"
                )
        return self


class CarrierEvent(SharedRecord):
    event_type: CarrierEventType
    event_time: str
    subject_type: str
    subject_id: str
    source: str
    location: str | None = None
    facility: str | None = None
    delay_minutes: int | None = None
    carrier_status: str | None = None
    raw_status: str | None = None

    @field_validator("event_time", mode="after")
    @classmethod
    def _validate_event_time(cls, v: str) -> str:
        res = validate_rfc3339_utc(v)
        if res is None:
            raise ValueError("event_time is required")
        return res

    @model_validator(mode="after")
    def _validate_carrier_event_evidence(self) -> CarrierEvent:
        if not self.evidence_ids:
            raise ValueError("CarrierEvent requires at least one evidence_id")
        return self


class InventoryPosition(SharedRecord):
    snapshot_at: str
    sku_id: str
    location_id: str
    on_hand: float
    allocated: float
    available: float
    on_order: float | None = None
    in_transit: float | None = None
    safety_stock: float | None = None
    reorder_point: float | None = None
    unit: str = "EA"

    @field_validator("snapshot_at", mode="after")
    @classmethod
    def _validate_snapshot_at(cls, v: str) -> str:
        res = validate_rfc3339_utc(v)
        if res is None:
            raise ValueError("snapshot_at is required")
        return res

    @model_validator(mode="after")
    def _available_identity(self) -> InventoryPosition:
        expected = self.on_hand - self.allocated
        if abs(expected - self.available) > 1e-9:
            raise ValueError(
                f"available must equal on_hand - allocated ({expected} != {self.available})"
            )
        return self


class SalesOrderLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: str
    ordered: float = Field(gt=0)
    allocated: float = Field(default=0, ge=0)
    shipped: float = Field(default=0, ge=0)


class SalesOrder(SharedRecord):
    sales_order_number: str
    order_status: str = "open"
    order_date: str | None = None
    requested_ship_date: str | None = None
    promised_ship_date: str | None = None
    customer_id: str | None = None
    priority: Priority | None = None
    ship_to_location_id: str | None = None
    currency: str | None = None
    lines: list[SalesOrderLine] = Field(default_factory=list)

    @field_validator("order_date", "requested_ship_date", "promised_ship_date", mode="after")
    @classmethod
    def _validate_order_dates(cls, v: str | None) -> str | None:
        return validate_rfc3339_or_date(v)


class SKU(SharedRecord):
    sku_code: str
    description: str
    base_unit: str = "EA"
    active: bool = True
    product_family: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    safety_stock: float | None = Field(default=None, ge=0)
    criticality: Literal["low", "medium", "high", "critical"] | None = None
    substitute_sku_ids: list[str] = Field(default_factory=list)
    country_of_origin: str | None = None
    dimensions_weight: dict | None = None


class Supplier(SharedRecord):
    supplier_code: str
    legal_name: str
    supplier_status: SupplierStatus = "active"
    addresses: list[dict | str] = Field(default_factory=list)
    facilities: list[str] = Field(default_factory=list)
    country: str | None = None
    supplier_risk_tier: str | None = None
    contact_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_supplier_invariants(self) -> Supplier:
        if not self.legal_name or not self.legal_name.strip():
            raise ValueError("Supplier legal_name cannot be empty")
        return self


class CalculationTraceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    rule_version: str = SCHEMA_VERSION
    inputs: dict
    outputs: dict
    description: str | None = None


class ImpactWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: str
    end: str | None = None
    method: str | None = None

    @field_validator("start", "end", mode="after")
    @classmethod
    def _validate_window_timestamps(cls, v: str | None) -> str | None:
        return validate_rfc3339_utc(v)

    @model_validator(mode="after")
    def _validate_window_order(self) -> ImpactWindow:
        if self.start and self.end and self.start > self.end:
            raise ValueError(f"Impact window start ({self.start}) cannot be after end ({self.end})")
        return self


class DelayRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_hours: float | None = None
    max_hours: float | None = None
    method: str

    @model_validator(mode="after")
    def _validate_range(self) -> DelayRange:
        if self.min_hours is not None and self.max_hours is not None:
            if self.min_hours > self.max_hours:
                raise ValueError(
                    f"min_hours ({self.min_hours}) cannot exceed max_hours ({self.max_hours})"
                )
        return self


class Exposure(SharedRecord):
    """Deterministic disruption consequence linked to a business entity."""

    event_id: str
    exposure_type: ExposureType
    exposure_status: ExposureStatus = "candidate"
    subject_type: SubjectType
    subject_id: str
    linkage_method: LinkageMethod
    impact_window: ImpactWindow
    expected_delay: DelayRange | None = None
    affected_sku_ids: list[str] = Field(default_factory=list)
    sales_order_ids: list[str] = Field(default_factory=list)
    inventory_risk: InventoryRisk | None = None
    financial_exposure: dict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    calculation_trace: list[CalculationTraceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _deterministic_linkage(self) -> Exposure:
        if self.linkage_method not in {
            "deterministic_geospatial",
            "deterministic_entity",
            "deterministic_time_window",
            "rule_based",
            "analyst_confirmed",
        }:
            raise ValueError(
                f"AI-only linkage ({self.linkage_method!r}) is prohibited; "
                "linkage must be deterministic or analyst_confirmed"
            )
        if not self.evidence_ids:
            raise ValueError("Exposure requires evidence_ids")
        if not self.calculation_trace:
            raise ValueError("Exposure requires calculation_trace")
        # Invariant: AI-only entity matches cannot confirm an Exposure
        if self.exposure_status == "confirmed":
            if self.linkage_method not in {
                "deterministic_geospatial",
                "deterministic_entity",
                "deterministic_time_window",
                "rule_based",
                "analyst_confirmed",
            }:
                raise ValueError("AI-only entity matches cannot confirm an Exposure")
        return self


class HumanApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: ApprovalState
    actor: str | None = None
    at: str | None = None
    notes: str | None = None

    @field_validator("at", mode="after")
    @classmethod
    def _validate_approval_time(cls, v: str | None) -> str | None:
        return validate_rfc3339_utc(v)

    @model_validator(mode="after")
    def _validate_approval_actor(self) -> HumanApproval:
        if self.state == "approved" and not self.actor:
            raise ValueError("Human approval requires an explicit actor")
        return self


class ExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str
    time: str
    external_ref: str | None = None

    @field_validator("time", mode="after")
    @classmethod
    def _validate_exec_time(cls, v: str) -> str:
        res = validate_rfc3339_utc(v)
        if res is None:
            raise ValueError("execution time is required")
        return res


class ModelTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    provider: str
    execution_class: Literal["local", "cloud"]
    prompt_version: str
    seed: int | None = None


class Recommendation(SharedRecord):
    """Advisory recommendation draft. Requires explicit human approval before any operational action."""

    exposure_ids: list[str]
    action_type: ActionType
    recommendation_status: RecommendationStatus = "draft"
    rationale: str
    assumptions: list[str] = Field(default_factory=list)
    priority: Priority = "medium"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    human_approval: HumanApproval
    execution_record: ExecutionRecord | None = None
    model_trace: ModelTrace | None = None

    @model_validator(mode="after")
    def _no_silent_execution(self) -> Recommendation:
        if not self.rationale or not self.rationale.strip():
            raise ValueError("Recommendation requires a non-empty rationale")
        # Actionable recommendations require linked exposure and evidence
        if self.action_type != "no_action":
            if not self.exposure_ids:
                raise ValueError("Material recommendation requires exposure_ids")
            if not self.evidence_ids:
                raise ValueError("Material recommendation requires evidence_ids")
        if self.recommendation_status == "approved" and self.human_approval.state != "approved":
            raise ValueError("approved recommendation requires human_approval.state=approved")
        if self.recommendation_status == "executed":
            if self.human_approval.state != "approved":
                raise ValueError("executed recommendation requires prior human approval")
            if self.execution_record is None:
                raise ValueError("executed recommendation requires execution_record")
        if self.human_approval.state == "approved" and not self.human_approval.actor:
            raise ValueError("human approval requires actor")
        return self


CANONICAL_MODELS: dict[str, type[BaseModel]] = {
    "Evidence": Evidence,
    "ExternalEvent": ExternalEvent,
    "PurchaseOrder": PurchaseOrder,
    "Shipment": Shipment,
    "ShipmentLeg": ShipmentLeg,
    "Container": Container,
    "CarrierEvent": CarrierEvent,
    "InventoryPosition": InventoryPosition,
    "SalesOrder": SalesOrder,
    "SKU": SKU,
    "Supplier": Supplier,
    "Exposure": Exposure,
    "Recommendation": Recommendation,
}
