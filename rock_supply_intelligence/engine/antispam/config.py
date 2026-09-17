"""Configurable thresholds, domain lists, and stale windows for the filter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rock_supply_intelligence.engine.profile import try_validate_alias_profile
from rock_supply_intelligence.engine.resolution import (
    ResolutionResult,
    is_blank,
    normalize_key,
    result,
)

RULE_VERSION = "source-quality-v0.1"

DEFAULT_BLOCKED_DOMAINS = (
    "spam-offers.example",
    "cheap-clicks.example",
    "bot-farm.invalid",
)

DEFAULT_CONTENT_FARM_DOMAINS = (
    "content-mill.example",
    "ezinearticles.com",
    "hubpages.com",
    "articlesbase.com",
)

DEFAULT_WIRE_DOMAINS = (
    "reuters.com",
    "apnews.com",
    "ap.org",
    "afp.com",
    "bloomberg.com",
    "bbc.com",
    "bbc.co.uk",
    "ft.com",
    "wsj.com",
    "nytimes.com",
    "theguardian.com",
)

DEFAULT_INDUSTRY_DOMAINS = (
    "joc.com",
    "lloydslist.com",
    "freightwaves.com",
    "gcaptain.com",
    "maritime-executive.com",
    "container-news.com",
    "seatrade-maritime.com",
)

TRACKING_QUERY_KEYS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "gclsrc",
        "mc_cid",
        "mc_eid",
        "igshid",
        "ref",
        "ref_src",
        "ncid",
        "ocid",
        "cmpid",
    }
)


class AntiSpamConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_version: str = RULE_VERSION
    min_text_chars: int = 40
    empty_text_chars: int = 24
    near_dup_hamming: int = 3
    syndication_hamming: int = 10
    title_near_dup_prefix: int = 80
    injection_quarantine: float = 0.55
    injection_review: float = 0.30
    advertisement_promo: float = 0.75
    advertisement_ops_max: float = 0.22
    seo_reject: float = 0.80
    spam_accept_max: float = 0.25
    quality_accept_min: float = 0.75
    operational_accept_min: float = 0.40
    review_spam_low: float = 0.28
    review_spam_high: float = 0.62
    stale_news_days: int = 90
    stale_community_days: int = 45
    # Authoritative / government records are valid historically.
    stale_authoritative_days: int | None = None
    blocked_domains: tuple[str, ...] = DEFAULT_BLOCKED_DOMAINS
    content_farm_domains: tuple[str, ...] = DEFAULT_CONTENT_FARM_DOMAINS
    wire_domains: tuple[str, ...] = DEFAULT_WIRE_DOMAINS
    industry_domains: tuple[str, ...] = DEFAULT_INDUSTRY_DOMAINS
    extra_domain_tiers: dict[str, str] = Field(default_factory=dict)
    field_aliases: list[dict[str, Any]] = Field(default_factory=list)
    allow_model: bool = True
    model_timeout_s: float = 60.0
    model_max_chars: int = 8000


VALID_REPUTATION_TIERS = frozenset(
    {"very_high", "high", "moderate_high", "moderate", "low", "very_low", "blocked", "unknown"}
)


def validate_antispam_config(config: AntiSpamConfig) -> ResolutionResult:
    """Fail closed on malformed domain/alias configuration."""
    stage = "antispam_config"
    for label, domains in (
        ("blocked_domains", config.blocked_domains),
        ("content_farm_domains", config.content_farm_domains),
        ("wire_domains", config.wire_domains),
        ("industry_domains", config.industry_domains),
    ):
        seen: dict[str, str] = {}
        for domain in domains:
            if not isinstance(domain, str) or is_blank(domain):
                return result(
                    status="INVALID_PROFILE",
                    reason=f"blank_domain_in_{label}",
                    input_identifier=repr(domain),
                    pipeline_stage=stage,
                    profile_version=config.rule_version,
                    code="CONFIG_ERROR",
                )
            key = normalize_key(domain)
            if key in seen:
                return result(
                    status="AMBIGUOUS",
                    reason=f"duplicate_domain_in_{label}",
                    input_identifier=domain,
                    normalized_identifier=key,
                    candidates=[seen[key], domain],
                    pipeline_stage=stage,
                    profile_version=config.rule_version,
                    code="AMBIGUOUS_ALIAS",
                )
            seen[key] = domain

    extra_seen: dict[str, str] = {}
    for domain, tier in config.extra_domain_tiers.items():
        if not isinstance(domain, str) or is_blank(domain):
            return result(
                status="INVALID_PROFILE",
                reason="blank_extra_domain_tier_key",
                input_identifier=repr(domain),
                pipeline_stage=stage,
                profile_version=config.rule_version,
                code="CONFIG_ERROR",
            )
        if not isinstance(tier, str) or tier not in VALID_REPUTATION_TIERS:
            return result(
                status="INVALID_PROFILE",
                reason="invalid_enum",
                input_identifier=str(tier),
                pipeline_stage=stage,
                profile_version=config.rule_version,
                code="CONFIG_ERROR",
            )
        key = normalize_key(domain)
        if key in extra_seen and extra_seen[key] != tier:
            return result(
                status="AMBIGUOUS",
                reason="conflicting_extra_domain_tier",
                input_identifier=domain,
                normalized_identifier=key,
                candidates=[extra_seen[key], tier],
                pipeline_stage=stage,
                profile_version=config.rule_version,
                code="AMBIGUOUS_ALIAS",
            )
        extra_seen[key] = tier

    blocked = {normalize_key(d) for d in config.blocked_domains}
    wire = {normalize_key(d) for d in config.wire_domains}
    clash = blocked & wire
    if clash:
        return result(
            status="AMBIGUOUS",
            reason="contradictory_configuration",
            input_identifier=next(iter(clash)),
            candidates=sorted(clash),
            pipeline_stage=stage,
            profile_version=config.rule_version,
            code="CONFIG_ERROR",
        )

    if config.field_aliases:
        _, alias_result = try_validate_alias_profile(
            {
                "profile_id": "antispam-field-aliases",
                "version": config.rule_version,
                "aliases": config.field_aliases,
            }
        )
        if alias_result.blocks_downstream:
            return alias_result.model_copy(update={"pipeline_stage": stage, "profile_version": config.rule_version})

    return result(
        status="VALID",
        reason="antispam_config_valid",
        input_identifier=config.rule_version,
        pipeline_stage=stage,
        profile_version=config.rule_version,
    )
