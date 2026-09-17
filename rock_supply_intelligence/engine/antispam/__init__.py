"""Source anti-spam, noise-reduction, and source-quality filter."""

from rock_supply_intelligence.engine.antispam.config import AntiSpamConfig, RULE_VERSION, validate_antispam_config
from rock_supply_intelligence.engine.antispam.duplicates import DuplicateIndex
from rock_supply_intelligence.engine.antispam.filter import apply_confidence_penalty, assess_source
from rock_supply_intelligence.engine.antispam.ingest import (
    evidence_from_assessment,
    event_confidence,
    filter_atomic_sample,
    filter_validated_source,
    quarantine_record,
    validated_from_atomic,
)

__all__ = [
    "AntiSpamConfig",
    "DuplicateIndex",
    "RULE_VERSION",
    "validate_antispam_config",
    "apply_confidence_penalty",
    "assess_source",
    "evidence_from_assessment",
    "event_confidence",
    "filter_atomic_sample",
    "filter_validated_source",
    "quarantine_record",
    "validated_from_atomic",
]
