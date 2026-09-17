"""Shared canonical field types and validators for contract v0.1."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "0.1"
TENANT_POC = "sunlighten-shadow"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]00:00)$"
)
RFC3339_ANY_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_rfc3339_utc(v: str | None) -> str | None:
    """Validate that value is a strictly compliant RFC 3339 UTC timestamp.

    Requires UTC offset ('Z' or '+00:00') and valid calendar date/time.
    """
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"Timestamp must be a string, got {type(v).__name__}")
    text = v.strip()
    if not text:
        raise ValueError("Timestamp cannot be empty")
    if not RFC3339_UTC_RE.match(text):
        raise ValueError(
            f"Timestamp {v!r} is not a valid RFC 3339 UTC timestamp. "
            "Expected format YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS+00:00."
        )
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date/time {v!r}: {exc}") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError(f"Timestamp {v!r} must have UTC offset (Z or +00:00)")
    return text


def validate_rfc3339_source(v: str | None) -> str | None:
    """Validate RFC 3339 timestamp with any valid timezone offset (for source precision)."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"Timestamp must be a string, got {type(v).__name__}")
    text = v.strip()
    if not text:
        return None
    if not RFC3339_ANY_RE.match(text):
        raise ValueError(
            f"Timestamp {v!r} is not a valid RFC 3339 timestamp with timezone offset"
        )
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid calendar date/time {v!r}: {exc}") from exc
    return text


def validate_rfc3339_or_date(v: str | None) -> str | None:
    """Validate RFC 3339 UTC timestamp or ISO 8601 date YYYY-MM-DD."""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"Date/timestamp must be a string, got {type(v).__name__}")
    text = v.strip()
    if not text:
        return None
    if ISO_DATE_RE.match(text):
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError as exc:
            raise ValueError(f"Invalid calendar date {v!r}: {exc}") from exc
    return validate_rfc3339_utc(text)


def validate_iso6346_checksum(container_number: str) -> bool:
    """Validate ISO 6346 container number check digit.

    Standard ISO 6346 format: 4 letters + 6 serial digits + 1 check digit.
    """
    s = container_number.strip().upper()
    if not re.match(r"^[A-Z]{4}\d{7}$", s):
        return False
    char_map = {
        "A": 10,
        "B": 12,
        "C": 13,
        "D": 14,
        "E": 15,
        "F": 16,
        "G": 17,
        "H": 18,
        "I": 19,
        "J": 20,
        "K": 21,
        "L": 23,
        "M": 24,
        "N": 25,
        "O": 26,
        "P": 27,
        "Q": 28,
        "R": 29,
        "S": 30,
        "T": 31,
        "U": 32,
        "V": 34,
        "W": 35,
        "X": 36,
        "Y": 37,
        "Z": 38,
    }
    total = sum((char_map[s[i]] if s[i] in char_map else int(s[i])) * (2**i) for i in range(10))
    check_digit = (total % 11) % 10
    return int(s[10]) == check_digit


RecordStatus = Literal["active", "superseded", "retracted", "archived", "draft"]
SourceType = Literal[
    "authoritative_feed",
    "government",
    "open_data",
    "news",
    "satellite",
    "community",
    "internal",
    "analyst",
]
ObservedOrInferred = Literal["observed", "extracted", "inferred", "calculated"]
EventType = Literal[
    "weather",
    "port_disruption",
    "vessel_anomaly",
    "earthquake",
    "labor",
    "geopolitical",
    "infrastructure",
    "carrier_exception",
    "customs_regulatory",
    "wildfire",
    "aviation_disruption",
    "road_disruption",
    "other",
]
EventState = Literal["reported", "confirmed", "ongoing", "resolved", "cancelled", "unknown"]
Severity = Literal["none", "low", "moderate", "high", "severe", "unknown"]
ShipmentStatus = Literal[
    "planned", "booked", "in_transit", "arrived", "delivered", "cancelled", "unknown"
]
Mode = Literal["ocean", "air", "road", "rail", "parcel", "multimodal"]
POStatus = Literal["draft", "open", "partially_received", "received", "cancelled", "closed"]
SupplierStatus = Literal["active", "inactive", "on_hold", "unknown"]
CarrierEventType = Literal[
    "departed",
    "arrived",
    "gated_in",
    "gated_out",
    "loaded",
    "discharged",
    "customs_hold",
    "exception",
    "eta_changed",
    "cancelled",
    "other",
]
ExposureType = Literal[
    "delay",
    "capacity_loss",
    "inventory_stockout",
    "customer_commitment",
    "financial",
    "compliance",
    "route_disruption",
]
ExposureStatus = Literal["candidate", "reviewed", "confirmed", "dismissed", "resolved"]
LinkageMethod = Literal[
    "deterministic_geospatial",
    "deterministic_entity",
    "deterministic_time_window",
    "rule_based",
    "analyst_confirmed",
]
SubjectType = Literal[
    "shipment",
    "shipment_leg",
    "container",
    "purchase_order",
    "sku",
    "sales_order",
    "supplier",
    "location",
]
ActionType = Literal[
    "monitor",
    "verify",
    "contact_carrier",
    "expedite_review",
    "allocate_review",
    "alternate_route_review",
    "customer_commitment_review",
    "compliance_review",
    "no_action",
]
RecommendationStatus = Literal[
    "draft",
    "pending_approval",
    "approved",
    "rejected",
    "executed",
    "withdrawn",
]
ApprovalState = Literal["not_requested", "pending", "approved", "rejected"]
Priority = Literal["low", "medium", "high", "urgent"]
InventoryRisk = Literal["none", "watch", "at_risk", "stockout_expected"]
ExtractionMethod = Literal["deterministic", "local_ai", "cloud_ai", "human", "pending"]
Split = Literal["dev", "selection", "holdout"]


class ExternalId(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system: str
    value: str
    url: str | None = None


class CanonicalRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_type: str
    id: str | None = None
    code: str | None = None
    name: str | None = None
    locode: str | None = None
    raw_value: str | None = None


class Confidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = Field(default=None, ge=0.0, le=1.0)
    method: str
    scope: str | None = None


class SharedRecord(BaseModel):
    """Base model enforcing contract-mandated shared audit and provenance fields."""

    model_config = ConfigDict(extra="forbid")

    id: str
    schema_version: Literal["0.1"] = SCHEMA_VERSION
    tenant_id: str = TENANT_POC
    status: RecordStatus
    created_at: str
    updated_at: str
    external_ids: list[ExternalId] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def _validate_shared_timestamps(cls, v: str) -> str:
        res = validate_rfc3339_utc(v)
        if res is None:
            raise ValueError("Audit timestamp cannot be None")
        return res
