"""Provider-neutral, observation-only vessel tracking contracts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rock_supply_intelligence.schemas.common import SHA256_RE, validate_rfc3339_utc

MMSI_RE = re.compile(r"^[0-9]{9}$")


class TrackingProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    source_locator: str
    received_at: str
    raw_sha256: str
    raw_ref: str
    synthetic: bool = False

    @field_validator("received_at")
    @classmethod
    def validate_received_at(cls, value: str) -> str:
        return validate_rfc3339_utc(value) or value

    @field_validator("raw_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if not SHA256_RE.match(value):
            raise ValueError("raw_sha256 must be a lowercase SHA-256 digest")
        return value


class VesselPosition(BaseModel):
    """An immutable provider observation. It is not a disruption event."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str
    mmsi: str
    vessel_name: str | None = None
    observed_at: str
    timestamp_basis: Literal["provider", "received_time_fallback"]
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    speed_over_ground_knots: float | None = Field(default=None, ge=0.0, le=102.3)
    course_over_ground_degrees: float | None = Field(default=None, ge=0.0, lt=360.0)
    true_heading_degrees: int | None = Field(default=None, ge=0, le=359)
    navigational_status: int | None = Field(default=None, ge=0, le=15)
    source_valid: bool
    provenance: TrackingProvenance

    @field_validator("mmsi")
    @classmethod
    def validate_mmsi(cls, value: str) -> str:
        value = value.strip()
        if not MMSI_RE.match(value) or value == "000000000":
            raise ValueError("mmsi must be a non-zero nine-digit identifier")
        return value

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: str) -> str:
        return validate_rfc3339_utc(value) or value

    @model_validator(mode="after")
    def validate_time_order(self) -> "VesselPosition":
        observed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        received = datetime.fromisoformat(self.provenance.received_at.replace("Z", "+00:00"))
        if observed > received:
            raise ValueError("observed_at cannot be after received_at")
        return self


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    south: float = Field(ge=-90.0, le=90.0)
    west: float = Field(ge=-180.0, le=180.0)
    north: float = Field(ge=-90.0, le=90.0)
    east: float = Field(ge=-180.0, le=180.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.south >= self.north:
            raise ValueError("south must be below north")
        if self.west >= self.east:
            raise ValueError("antimeridian-crossing boxes must be split explicitly")
        return self

    def contains(self, latitude: float, longitude: float) -> bool:
        return self.south <= latitude <= self.north and self.west <= longitude <= self.east


class PortGeofence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locode: str
    name: str
    bounds: BoundingBox

    @field_validator("locode")
    @classmethod
    def validate_locode(cls, value: str) -> str:
        value = value.strip().upper()
        if not re.match(r"^[A-Z]{2}[A-Z0-9]{3}$", value):
            raise ValueError("locode must be a five-character UN/LOCODE")
        return value


class VesselGeofenceSignal(BaseModel):
    """Deterministic observation requiring review; never an ExternalEvent."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str
    observation_id: str
    mmsi: str
    port_locode: str
    observed_at: str
    relation: Literal["inside", "outside", "unknown"]
    transition: Literal["entered", "exited", "continued_inside", "continued_outside", "first_observation", "unknown"]
    reason: str
    review_state: Literal["review"] = "review"
    external_event_eligible: Literal[False] = False


class NormalizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Literal["accepted", "ignored", "quarantined"]
    observation: VesselPosition | None = None
    reason: str
    raw_sha256: str

    @model_validator(mode="after")
    def validate_disposition(self) -> "NormalizationResult":
        if self.disposition == "accepted" and self.observation is None:
            raise ValueError("accepted normalization requires an observation")
        if self.disposition != "accepted" and self.observation is not None:
            raise ValueError("non-accepted normalization cannot expose an observation")
        return self
