"""Ingest gate: validated source → anti-spam filter → Evidence eligibility.

Does not create ExternalEvent records for rejected, quarantined, or
non-canonical syndicated copies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from rock_supply_intelligence.engine.antispam.config import AntiSpamConfig
from rock_supply_intelligence.engine.antispam.duplicates import DuplicateIndex
from rock_supply_intelligence.engine.antispam.filter import apply_confidence_penalty, assess_source
from rock_supply_intelligence.providers.base import InferenceProvider
from rock_supply_intelligence.schemas.atomic import AtomicSample
from rock_supply_intelligence.schemas.canonical import Evidence, ExtractionTrace
from rock_supply_intelligence.schemas.common import SCHEMA_VERSION, TENANT_POC
from rock_supply_intelligence.schemas.source_quality import SourceQualityAssessment, ValidatedSource


def validated_from_atomic(sample: AtomicSample, text: str, html: str | None = None) -> ValidatedSource:
    src = sample.source
    body = text or ""
    html_body = html
    ctype = (src.content_type or "").lower()
    if html_body is None and ("html" in ctype or body.lstrip()[:15].lower().startswith("<!doctype html") or "<html" in body[:400].lower()):
        html_body = body
    return ValidatedSource(
        source_id=src.source_id or sample.sample_id,
        source_name=src.source_name,
        source_type=src.source_type,
        source_locator=src.source_locator,
        publisher=src.publisher,
        source_authority=src.source_authority,
        source_reliability=src.source_reliability,
        retrieved_at=src.retrieved_at or "1970-01-01T00:00:00Z",
        published_at=src.published_at,
        observed_at=src.observed_at,
        effective_at=src.effective_at,
        content_hash=src.content_hash,
        raw_ref=src.raw_ref,
        content_type=src.content_type,
        language=src.language,
        title=src.source_name,
        text=body,
        html=html_body,
    )


def filter_validated_source(
    source: ValidatedSource,
    *,
    index: DuplicateIndex | None = None,
    config: AntiSpamConfig | None = None,
    provider: InferenceProvider | None = None,
    as_of: str | None = None,
) -> SourceQualityAssessment:
    return assess_source(source, index=index, config=config, provider=provider, as_of=as_of)


def filter_atomic_sample(
    sample: AtomicSample,
    text: str,
    *,
    html: str | None = None,
    index: DuplicateIndex | None = None,
    config: AntiSpamConfig | None = None,
    provider: InferenceProvider | None = None,
    as_of: str | None = None,
) -> SourceQualityAssessment:
    source = validated_from_atomic(sample, text, html=html)
    return filter_validated_source(source, index=index, config=config, provider=provider, as_of=as_of)


def evidence_from_assessment(
    source: ValidatedSource,
    assessment: SourceQualityAssessment,
    *,
    evidence_id: str | None = None,
    excerpt_or_payload_path: str | None = None,
    now: str | None = None,
) -> Evidence | None:
    """Build Evidence only when the filter allows it. Quarantine/reject stay audit-only."""
    if not assessment.evidence_eligible:
        return None
    ts = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status = "active" if assessment.source_quality.decision in {"accept", "accept_with_penalty"} else "draft"
    method = "deterministic"
    if assessment.source_quality.method == "hybrid":
        method = "local_ai"
    elif assessment.source_quality.method == "local_ai":
        method = "local_ai"
    return Evidence(
        id=evidence_id or f"EVD-{source.source_id}",
        status=status,  # type: ignore[arg-type]
        created_at=ts,
        updated_at=ts,
        tenant_id=TENANT_POC,
        schema_version=SCHEMA_VERSION,
        source_name=source.source_name,
        source_type=source.source_type,
        source_locator=source.source_locator,
        publisher=source.publisher,
        source_authority=source.source_authority,
        retrieved_at=source.retrieved_at,
        published_at=source.published_at,
        observed_at=source.observed_at,
        effective_at=source.effective_at,
        content_hash=assessment.content_hash or source.content_hash,
        hash_method="sha256",
        raw_ref=source.raw_ref,
        excerpt_or_payload_path=excerpt_or_payload_path or source.raw_ref,
        language=source.language,
        extraction=ExtractionTrace(
            method=method,  # type: ignore[arg-type]
            model_or_rule=assessment.audit.rule_version,
            prompt_version=None
            if assessment.source_quality.method == "deterministic"
            else "source-quality-v0.1.0",
            execution_class="deterministic"
            if assessment.source_quality.method == "deterministic"
            else "local",
        ),
        source_quality=assessment.source_quality,
    )


def event_confidence(
    base: float | None,
    assessment: SourceQualityAssessment,
) -> float | None:
    if not assessment.event_eligible:
        return None
    return apply_confidence_penalty(base, assessment.source_quality)


def quarantine_record(source: ValidatedSource, assessment: SourceQualityAssessment) -> dict[str, Any]:
    """Minimal audit payload for reject/quarantine. Not Evidence."""
    return {
        "record_type": "source_quality_audit",
        "schema_version": SCHEMA_VERSION,
        "source_id": source.source_id,
        "source_locator": source.source_locator,
        "raw_ref": source.raw_ref,
        "content_hash": assessment.content_hash,
        "decision": assessment.source_quality.decision,
        "spam_class": assessment.source_quality.spam_class,
        "source_quality": assessment.source_quality.model_dump(),
        "duplicate_of": assessment.duplicate_of,
        "canonical_source_id": assessment.canonical_source_id,
        "retained": assessment.source_quality.decision != "reject",
    }
