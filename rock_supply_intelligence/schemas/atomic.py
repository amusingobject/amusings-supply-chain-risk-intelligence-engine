"""Pydantic models for atomic OSINT sample manifests (benchmark v0.1)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SAMPLE_ID_RE = re.compile(r"^ATOM-[A-Z0-9-]+$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

Split = Literal["dev", "selection", "holdout"]
CollectionStatus = Literal["planned", "collected", "redacted", "unavailable"]
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
Language = Literal["en", "zh-TW", "mixed"]
PrimaryClass = Literal[
    "materially_relevant",
    "monitor",
    "irrelevant",
    "ambiguous_conflicting",
    "prompt_injection",
]
Disposition = Literal["normalize", "monitor", "suppress", "abstain", "quarantine"]
ContentStatus = Literal["metadata_only", "lawful_capture", "redacted_excerpt"]


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: str | None = None
    source_name: str
    source_type: SourceType
    publisher: str | None = None
    source_authority: str | None = None
    source_reliability: str | None = None
    source_locator: str
    language: Language
    content_type: str | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    effective_at: str | None = None
    observed_at: str | None = None
    raw_ref: str
    content_hash: str | None = None
    hash_method: Literal["sha256"] | None = "sha256"
    license: str | None = None
    access_constraints: str | None = None

    @field_validator("content_hash")
    @classmethod
    def _hash_shape(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not SHA256_RE.match(value):
            raise ValueError("content_hash must be 64 lowercase hex chars")
        return value


class LabelRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    primary_class: PrimaryClass
    primary_label: str | None = None
    event_category: str
    event_type: str | None = None
    event_subtype: str | None = None
    expected_relevance_class: PrimaryClass | None = None
    expected_disposition: Disposition
    tasks: list[str] = Field(default_factory=list)


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    collection_plan_id: str
    collector_id: str | None = None
    collector_version: str | None = None
    ingestion_method: str | None = None
    pipeline_run_id: str | None = None
    transformations: list[str] = Field(default_factory=list)
    ai_used: bool = False
    synthetic: bool = False
    content_status: ContentStatus
    notes: str | None = None
    adjudication_status: str | None = None


class AtomicSample(BaseModel):
    model_config = ConfigDict(extra="allow")

    sample_id: str
    schema_version: Literal["0.1"]
    split: Split
    collection_status: CollectionStatus
    source: SourceRecord
    labels: LabelRecord
    provenance: ProvenanceRecord

    @field_validator("sample_id")
    @classmethod
    def _sample_id(cls, value: str) -> str:
        if not SAMPLE_ID_RE.match(value):
            raise ValueError(f"invalid sample_id: {value}")
        return value
