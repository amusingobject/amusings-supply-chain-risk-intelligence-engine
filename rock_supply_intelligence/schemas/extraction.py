"""Canonical model output for atomic OSINT classification/extraction."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RelevanceClass = Literal[
    "materially_relevant",
    "monitor",
    "irrelevant",
    "ambiguous_conflicting",
    "prompt_injection",
]
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


class ExtractedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    value: str
    normalized_value: str | None = None
    evidence_span: str | None = None


class GroundedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    evidence_span: str | None = None
    supported_by_source: bool
    critical: bool = False


class CandidateEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    event_state: EventState
    title: str
    severity: Severity
    start_time: str | None = None
    end_time: str | None = None
    locations: list[ExtractedEntity] = Field(default_factory=list)
    entities: list[ExtractedEntity] = Field(default_factory=list)


class AtomicExtractionOutput(BaseModel):
    """Provider-agnostic structured result for one atomic OSINT sample."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = "0.1"
    sample_id: str
    relevance_class: RelevanceClass
    prompt_injection_detected: bool = False
    operational_action_attempted: bool = False
    invented_business_fact: bool = False
    abstain: bool = False
    event: CandidateEvent | None = None
    claims: list[GroundedClaim] = Field(default_factory=list)
    unsupported_critical_claims: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None


ATOMIC_EXTRACTION_JSON_SCHEMA = AtomicExtractionOutput.model_json_schema()
