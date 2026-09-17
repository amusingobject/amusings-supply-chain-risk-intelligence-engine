"""Canonical source-quality / anti-spam types for the OSINT ingest filter.

Sits after source validation and before Evidence / ExternalEvent creation.
Scores are 0.0–1.0 and must come from deterministic signals (and, when used,
calibrated model flags) — never from model self-confidence alone.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, SourceType

SPAM_CLASS_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
REASON_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

SPAM_CLASSES = (
    "clean",
    "duplicate",
    "near_duplicate",
    "promotional",
    "advertisement",
    "seo_spam",
    "content_farm",
    "scraped_repost",
    "low_information",
    "irrelevant_boilerplate",
    "social_spam",
    "stale_repost",
    "clickbait",
    "suspicious",
    "prompt_injection",
    "malformed",
    "unknown",
)

SpamClass = Literal[
    "clean",
    "duplicate",
    "near_duplicate",
    "promotional",
    "advertisement",
    "seo_spam",
    "content_farm",
    "scraped_repost",
    "low_information",
    "irrelevant_boilerplate",
    "social_spam",
    "stale_repost",
    "clickbait",
    "suspicious",
    "prompt_injection",
    "malformed",
    "unknown",
]

FilterDecision = Literal["accept", "accept_with_penalty", "quarantine", "reject", "review"]
FilterMethod = Literal["deterministic", "hybrid", "local_ai", "human"]
ReputationTier = Literal[
    "very_high",
    "high",
    "moderate_high",
    "moderate",
    "low",
    "very_low",
    "blocked",
    "unknown",
]
ContentKind = Literal["html", "json", "xml", "text", "pdf_placeholder", "binary", "empty"]


def _score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class SourceQuality(BaseModel):
    """Canonical quality object attached to a filtered source / Evidence."""

    model_config = ConfigDict(extra="forbid")

    spam_class: str
    quality_score: float = Field(ge=0.0, le=1.0)
    spam_score: float = Field(ge=0.0, le=1.0)
    operational_value_score: float = Field(ge=0.0, le=1.0)
    duplicate_probability: float = Field(ge=0.0, le=1.0)
    prompt_injection_score: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    decision: FilterDecision
    method: FilterMethod = "deterministic"
    model_used: str | None = None

    @field_validator("spam_class")
    @classmethod
    def _spam_class(cls, value: str) -> str:
        token = value.strip().lower()
        if not SPAM_CLASS_RE.match(token):
            raise ValueError(f"invalid spam_class: {value}")
        return token

    @field_validator("reasons")
    @classmethod
    def _reasons(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in value:
            token = item.strip().lower().replace(" ", "_")
            if not REASON_RE.match(token):
                raise ValueError(f"invalid reason token: {item}")
            if token not in seen:
                seen.add(token)
                out.append(token)
        return out

    @field_validator(
        "quality_score",
        "spam_score",
        "operational_value_score",
        "duplicate_probability",
        "prompt_injection_score",
    )
    @classmethod
    def _clamp(cls, value: float) -> float:
        return round(_score(value), 4)


class QualitySignals(BaseModel):
    """Deterministic feature snapshot. Audit-only; not a business fact."""

    model_config = ConfigDict(extra="forbid")

    content_kind: ContentKind
    char_count: int = 0
    extracted_char_count: int = 0
    token_count: int = 0
    unique_token_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    boilerplate_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    repeated_paragraph_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    html_to_text_ratio: float | None = Field(default=None, ge=0.0)
    malformed_markup: bool = False
    missing_body: bool = False
    promotional_score: float = Field(default=0.0, ge=0.0, le=1.0)
    affiliate_link_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    seo_score: float = Field(default=0.0, ge=0.0, le=1.0)
    social_spam_score: float = Field(default=0.0, ge=0.0, le=1.0)
    clickbait_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_filler_score: float = Field(default=0.0, ge=0.0, le=1.0)
    headline_body_support: float | None = Field(default=None, ge=0.0, le=1.0)
    operational_keyword_density: float = Field(default=0.0, ge=0.0, le=1.0)
    structured_fact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    prompt_injection_score: float = Field(default=0.0, ge=0.0, le=1.0)
    stale_days: float | None = None
    reputation_tier: ReputationTier = "unknown"
    reputation_score: float = Field(default=0.5, ge=0.0, le=1.0)
    domain: str | None = None
    canonical_url: str | None = None
    content_sha256: str | None = None
    simhash: str | None = None
    title_normalized: str | None = None


class SyndicationInfo(BaseModel):
    """Syndicated copies share one canonical intelligence document."""

    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    is_canonical: bool
    canonical_source_id: str
    demotes_source_id: str | None = None
    alternate_source_ids: list[str] = Field(default_factory=list)
    original_publisher: str | None = None
    match_method: str


class QualityModelOutput(BaseModel):
    """Structured local-model output for ambiguous quality cases.

    Flags only. Numeric scores remain deterministic.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = SCHEMA_VERSION
    spam_class: str
    decision: FilterDecision
    clickbait: bool = False
    promotional_but_factual: bool = False
    ai_generated_filler: bool = False
    operational_facts_present: bool = False
    headline_supported_by_body: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("spam_class")
    @classmethod
    def _spam_class(cls, value: str) -> str:
        token = value.strip().lower()
        if not SPAM_CLASS_RE.match(token):
            raise ValueError(f"invalid spam_class: {value}")
        return token


class ValidatedSource(BaseModel):
    """Input to the anti-spam layer. Assumes source validation already ran."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_name: str
    source_type: SourceType
    source_locator: str
    publisher: str | None = None
    source_authority: str | None = None
    source_reliability: str | None = None
    retrieved_at: str
    published_at: str | None = None
    observed_at: str | None = None
    effective_at: str | None = None
    content_hash: str | None = None
    raw_ref: str
    content_type: str | None = None
    language: str | None = None
    title: str | None = None
    text: str = ""
    html: str | None = None
    rss_guid: str | None = None


class FilterAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_version: str
    model_invoked: bool = False
    model_blocked_by_hard_gate: bool = False
    hard_gate: str | None = None
    notes: list[str] = Field(default_factory=list)


class SourceQualityAssessment(BaseModel):
    """Pipeline result: classify, score, and gate Evidence / ExternalEvent."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.1"] = SCHEMA_VERSION
    source_id: str
    source_locator: str
    content_hash: str | None = None
    source_quality: SourceQuality
    signals: QualitySignals
    syndication: SyndicationInfo | None = None
    evidence_eligible: bool
    event_eligible: bool
    duplicate_of: str | None = None
    canonical_source_id: str | None = None
    alternate_source_ids: list[str] = Field(default_factory=list)
    audit: FilterAudit

    def as_source_quality_dict(self) -> dict[str, Any]:
        return {"source_quality": self.source_quality.model_dump()}


QUALITY_MODEL_JSON_SCHEMA = QualityModelOutput.model_json_schema()
