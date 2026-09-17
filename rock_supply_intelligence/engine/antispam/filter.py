"""Deterministic-first source anti-spam and quality filter.

Obvious spam never reaches a local model. Ambiguous cases may, and only then
as flags that cannot override hard gates or become scores by themselves.
"""

from __future__ import annotations

from rock_supply_intelligence.engine.antispam.classifier import apply_model_constraints, classify_ambiguous
from rock_supply_intelligence.engine.antispam.config import AntiSpamConfig, RULE_VERSION, validate_antispam_config
from rock_supply_intelligence.engine.resolution import ResolutionResult
from rock_supply_intelligence.engine.antispam.duplicates import (
    DuplicateIndex,
    DuplicateMatch,
    IndexedDocument,
)
from rock_supply_intelligence.engine.antispam.reputation import lookup_reputation
from rock_supply_intelligence.engine.antispam.signals import clamp01, extract_signals, extract_text
from rock_supply_intelligence.providers.base import InferenceProvider
from rock_supply_intelligence.schemas.source_quality import (
    FilterAudit,
    FilterDecision,
    QualityModelOutput,
    QualitySignals,
    SourceQuality,
    SourceQualityAssessment,
    SyndicationInfo,
    ValidatedSource,
)

PROTECTED_TIERS = frozenset({"very_high", "high"})


def _halt_invalid_config(
    source: ValidatedSource,
    signals: QualitySignals,
    cfg_result: ResolutionResult,
    config: AntiSpamConfig,
) -> SourceQualityAssessment:
    """Invalid/ambiguous config never yields accept. Retain for review."""
    injection = signals.prompt_injection_score >= 0.55
    return SourceQualityAssessment(
        source_id=source.source_id,
        source_locator=source.source_locator,
        content_hash=signals.content_sha256,
        source_quality=SourceQuality(
            spam_class="prompt_injection" if injection else "unknown",
            quality_score=0.0,
            spam_score=max(signals.prompt_injection_score, 0.5),
            operational_value_score=0.0,
            duplicate_probability=0.0,
            prompt_injection_score=signals.prompt_injection_score,
            reasons=["invalid_profile", "review_required"],
            decision="quarantine",
            method="deterministic",
            model_used=None,
        ),
        signals=signals,
        syndication=None,
        evidence_eligible=False,
        event_eligible=False,
        duplicate_of=None,
        canonical_source_id=None,
        alternate_source_ids=[],
        audit=FilterAudit(
            rule_version=config.rule_version or RULE_VERSION,
            model_invoked=False,
            model_blocked_by_hard_gate=True,
            hard_gate="invalid_profile",
            notes=[cfg_result.reason, cfg_result.code or cfg_result.status],
        ),
    )


def assess_source(
    source: ValidatedSource,
    *,
    index: DuplicateIndex | None = None,
    config: AntiSpamConfig | None = None,
    provider: InferenceProvider | None = None,
    as_of: str | None = None,
) -> SourceQualityAssessment:
    config = config or AntiSpamConfig()
    index = index if index is not None else DuplicateIndex()
    cfg_result = validate_antispam_config(config)
    if cfg_result.blocks_downstream:
        safe = AntiSpamConfig()
        reputation = lookup_reputation(source, safe)
        signals = extract_signals(source, reputation, as_of=as_of)
        return _halt_invalid_config(source, signals, cfg_result, config)
    reputation = lookup_reputation(source, config)
    signals = extract_signals(source, reputation, as_of=as_of)
    matches = index.lookup(
        content_sha256=signals.content_sha256 or "",
        canonical_url=signals.canonical_url,
        title_normalized=signals.title_normalized,
        published_at=source.published_at or source.effective_at,
        simhash=int(signals.simhash or "0", 16),
        rss_guid=source.rss_guid,
        near_dup_hamming=config.near_dup_hamming,
        syndication_hamming=config.syndication_hamming,
    )

    scores = _scores(signals, matches, config)
    tentative = _deterministic_decision(source, signals, matches, scores, config)
    tentative = _apply_duplicate_gates(source, signals, matches, index, tentative)
    syndication = _syndication(source, signals, matches, scores, index, tentative)

    hard_gate = tentative.get("hard_gate")
    decision: FilterDecision = tentative["decision"]
    spam_class: str = tentative["spam_class"]
    reasons: list[str] = list(tentative["reasons"])
    method = "deterministic"
    model_used = None
    model_invoked = False
    model_blocked = False
    notes: list[str] = list(tentative.get("notes") or [])

    if decision == "review" and provider is not None and config.allow_model and hard_gate is None:
        model_invoked = True
        content = _model_content(source, signals)
        model = classify_ambiguous(
            provider,
            source,
            content,
            {
                "spam_class": spam_class,
                "spam_score": scores["spam_score"],
                "operational_value_score": scores["operational_value_score"],
                "quality_score": scores["quality_score"],
                "prompt_injection_score": scores["prompt_injection_score"],
                "clickbait_score": signals.clickbait_score,
                "promotional_score": signals.promotional_score,
                "reputation_tier": signals.reputation_tier,
            },
            max_chars=config.model_max_chars,
            timeout_s=config.model_timeout_s,
        )
        if model is not None:
            constrained = apply_model_constraints(
                hard_decision=None,
                hard_class=None,
                spam_score=scores["spam_score"],
                injection_score=scores["prompt_injection_score"],
                model=model,
            )
            decision, spam_class, reasons, scores = _blend_model(
                decision, spam_class, reasons, scores, constrained
            )
            method = "hybrid"
            model_used = getattr(provider, "model", None) or getattr(provider, "name", "local")
        else:
            notes.append("model_unparseable_quarantine")
            decision = "quarantine"
            if spam_class == "clean":
                spam_class = "unknown"
    elif decision == "review" and (provider is None or not config.allow_model):
        notes.append("review_without_model_quarantine")
        decision = "quarantine"
        if spam_class in {"clean", "unknown"}:
            spam_class = "unknown"
    elif decision == "review" and hard_gate:
        model_blocked = True

    if syndication and not syndication.is_canonical and decision in {"accept", "accept_with_penalty", "review"}:
        decision = "accept_with_penalty"
        if spam_class == "clean":
            spam_class = "scraped_repost"
        if "syndicated_copy" not in reasons:
            reasons.append("syndicated_copy")

    evidence_eligible, event_eligible = _eligibility(decision, syndication)
    quality = SourceQuality(
        spam_class=spam_class,
        quality_score=scores["quality_score"],
        spam_score=scores["spam_score"],
        operational_value_score=scores["operational_value_score"],
        duplicate_probability=scores["duplicate_probability"],
        prompt_injection_score=scores["prompt_injection_score"],
        reasons=reasons,
        decision=decision,
        method=method,  # type: ignore[arg-type]
        model_used=model_used,
    )
    duplicate_of = None
    for match in matches:
        if match.kind in {"exact_hash", "canonical_url", "rss_guid", "near_duplicate"}:
            duplicate_of = match.source_id
            break
    canonical_id = syndication.canonical_source_id if syndication else source.source_id
    alternates = list(syndication.alternate_source_ids) if syndication else []

    result = SourceQualityAssessment(
        source_id=source.source_id,
        source_locator=source.source_locator,
        content_hash=signals.content_sha256,
        source_quality=quality,
        signals=signals,
        syndication=syndication,
        evidence_eligible=evidence_eligible,
        event_eligible=event_eligible,
        duplicate_of=duplicate_of,
        canonical_source_id=canonical_id,
        alternate_source_ids=alternates,
        audit=FilterAudit(
            rule_version=config.rule_version or RULE_VERSION,
            model_invoked=model_invoked,
            model_blocked_by_hard_gate=model_blocked,
            hard_gate=hard_gate,
            notes=notes,
        ),
    )
    index.register(
        IndexedDocument(
            source_id=source.source_id,
            content_sha256=signals.content_sha256 or "",
            canonical_url=signals.canonical_url,
            title_normalized=signals.title_normalized,
            simhash=int(signals.simhash or "0", 16),
            domain=signals.domain,
            publisher=source.publisher,
            published_at=source.published_at or source.effective_at,
            source_type=source.source_type,
            reputation_score=signals.reputation_score,
            rss_guid=source.rss_guid,
        )
    )
    if syndication:
        members = index.clusters.setdefault(syndication.cluster_id, [])
        if source.source_id not in members:
            members.append(source.source_id)
        if syndication.canonical_source_id not in members:
            members.append(syndication.canonical_source_id)
        index.canonical_of[syndication.cluster_id] = syndication.canonical_source_id
    return result


def apply_confidence_penalty(base: float | None, quality: SourceQuality) -> float | None:
    """Blend extraction confidence with source quality. Never invents facts."""
    if quality.decision in {"reject", "quarantine", "review"}:
        return None
    prior = 0.7 if base is None else clamp01(base)
    if quality.decision == "accept":
        return round(clamp01(prior * (0.55 + 0.45 * quality.quality_score)), 4)
    return round(
        clamp01(prior * quality.quality_score * (1.0 - 0.45 * quality.spam_score)),
        4,
    )


def _scores(
    signals: QualitySignals,
    matches: list[DuplicateMatch],
    config: AntiSpamConfig,
) -> dict[str, float]:
    dup = 0.0
    for match in matches:
        dup = max(dup, match.probability)
    injection = signals.prompt_injection_score
    spam = clamp01(
        0.28 * signals.promotional_score
        + 0.18 * signals.seo_score
        + 0.12 * signals.boilerplate_ratio
        + 0.12 * signals.social_spam_score
        + 0.10 * signals.clickbait_score
        + 0.08 * signals.ai_filler_score
        + 0.12 * injection
        + (0.35 if signals.extracted_char_count < config.empty_text_chars else 0.0)
        + (0.20 if signals.malformed_markup and signals.extracted_char_count < 80 else 0.0)
    )
    if signals.reputation_tier == "blocked":
        spam = max(spam, 0.95)
    ops = clamp01(
        0.45 * signals.operational_keyword_density
        + 0.35 * signals.structured_fact_score
        + 0.20 * signals.reputation_score
    )
    if signals.content_kind in {"json", "xml"} and signals.reputation_tier in PROTECTED_TIERS:
        ops = max(ops, 0.8)
    integrity = 0.5
    if signals.extracted_char_count >= 400:
        integrity = 0.85
    elif signals.extracted_char_count >= config.min_text_chars:
        integrity = 0.65
    elif signals.content_kind in {"json", "xml"}:
        integrity = 0.8
    elif signals.content_kind == "pdf_placeholder":
        integrity = 0.4
    else:
        integrity = 0.15
    if signals.malformed_markup:
        integrity *= 0.5
    integrity = clamp01(integrity * (0.5 + 0.5 * signals.unique_token_ratio) if signals.token_count else integrity)
    quality = clamp01(
        0.32 * signals.reputation_score
        + 0.24 * integrity
        + 0.24 * (1.0 - spam)
        + 0.20 * ops
    )
    if dup >= 0.99:
        quality = min(quality, 0.45)
    return {
        "quality_score": round(quality, 4),
        "spam_score": round(spam, 4),
        "operational_value_score": round(ops, 4),
        "duplicate_probability": round(dup, 4),
        "prompt_injection_score": round(injection, 4),
    }


def _deterministic_decision(
    source: ValidatedSource,
    signals: QualitySignals,
    matches: list[DuplicateMatch],
    scores: dict[str, float],
    config: AntiSpamConfig,
) -> dict:
    reasons: list[str] = []
    notes: list[str] = []
    protected = signals.reputation_tier in PROTECTED_TIERS

    if signals.reputation_tier == "blocked":
        return _gate("reject", "suspicious", ["blocked_domain"], "blocked_domain")

    if scores["prompt_injection_score"] >= config.injection_quarantine:
        return _gate(
            "quarantine",
            "prompt_injection",
            ["prompt_injection_patterns"],
            "prompt_injection",
        )

    empty = signals.extracted_char_count < config.empty_text_chars and signals.content_kind not in {
        "json",
        "xml",
        "pdf_placeholder",
    }
    if empty:
        return _gate("reject", "low_information", ["empty_or_near_empty"], "empty")

    if signals.content_kind == "pdf_placeholder" and protected:
        reasons.append("authoritative_source")
        return {
            "decision": "accept_with_penalty",
            "spam_class": "unknown",
            "reasons": reasons + ["low_information_capture"],
            "hard_gate": None,
            "notes": ["pdf_unextracted"],
        }

    if signals.content_kind == "binary" and not protected:
        return _gate("reject", "malformed", ["malformed_markup"], "malformed")
    if signals.malformed_markup and (
        signals.extracted_char_count < 80 or signals.unique_token_ratio < 0.12
    ) and not protected:
        return _gate("reject", "malformed", ["malformed_markup", "missing_body"], "malformed")

    # Exact / near-duplicate gates run in _apply_duplicate_gates so same-domain
    # copies reject while cross-domain wire copies can syndicate.

    if not protected and signals.promotional_score >= config.advertisement_promo and (
        scores["operational_value_score"] < config.advertisement_ops_max
        or signals.affiliate_link_ratio >= 0.4
    ):
        cls = "advertisement" if signals.affiliate_link_ratio >= 0.25 or signals.promotional_score >= 0.85 else "promotional"
        return _gate(
            "reject",
            cls,
            ["excessive_affiliate_links", "sponsored_or_advertorial"]
            if signals.affiliate_link_ratio >= 0.2
            else ["promotional_language"],
            "advertisement",
        )

    if not protected and signals.social_spam_score >= 0.65 and (
        scores["operational_value_score"] < 0.25 or signals.extracted_char_count < 140
    ):
        return _gate("reject", "social_spam", ["social_spam_markers"], "social_spam")

    if signals.seo_score >= config.seo_reject and scores["operational_value_score"] < 0.25 and not protected:
        cls = "content_farm" if signals.reputation_tier == "very_low" else "seo_spam"
        return _gate("reject", cls, ["keyword_stuffing"], "seo_spam")

    if signals.reputation_tier == "very_low" and scores["operational_value_score"] < 0.3:
        return _gate("quarantine", "content_farm", ["content_farm_domain"], "content_farm")

    stale = _is_stale(source, signals, config)
    if stale:
        return _gate("quarantine", "stale_repost", ["stale_publication"], "stale")

    if protected:
        reasons.append("authoritative_source")
        if scores["operational_value_score"] >= 0.35 or signals.content_kind in {"json", "xml"}:
            reasons.append("substantive_operational_content")
        if scores["prompt_injection_score"] >= config.injection_review:
            return {
                "decision": "quarantine",
                "spam_class": "suspicious",
                "reasons": reasons + ["prompt_injection_patterns"],
                "hard_gate": "prompt_injection_review",
                "notes": notes,
            }
        return {
            "decision": "accept",
            "spam_class": "clean",
            "reasons": reasons,
            "hard_gate": None,
            "notes": notes,
        }

    if scores["prompt_injection_score"] >= config.injection_review:
        return {
            "decision": "quarantine",
            "spam_class": "suspicious",
            "reasons": ["prompt_injection_patterns"],
            "hard_gate": None,
            "notes": notes,
        }

    if signals.clickbait_score >= 0.5 and (signals.headline_body_support or 1.0) < 0.45:
        if scores["operational_value_score"] < 0.2:
            return _gate("reject", "clickbait", ["sensational_headline"], "clickbait")
        return {
            "decision": "review",
            "spam_class": "clickbait",
            "reasons": ["sensational_headline"],
            "hard_gate": None,
            "notes": notes,
        }

    if (
        signals.promotional_score >= 0.35
        and scores["operational_value_score"] >= 0.35
    ):
        return {
            "decision": "accept_with_penalty",
            "spam_class": "promotional",
            "reasons": ["promotional_language", "substantive_operational_content"],
            "hard_gate": None,
            "notes": notes,
        }

    if signals.reputation_tier in {"low", "very_low", "unknown"} and scores["operational_value_score"] >= 0.45:
        return {
            "decision": "accept_with_penalty",
            "spam_class": "clean" if signals.reputation_tier != "very_low" else "suspicious",
            "reasons": ["low_source_reputation", "substantive_operational_content"],
            "hard_gate": None,
            "notes": notes,
        }

    if signals.ai_filler_score >= 0.5 and scores["operational_value_score"] >= 0.3:
        return {
            "decision": "review",
            "spam_class": "low_information",
            "reasons": ["ai_filler_language", "substantive_operational_content"],
            "hard_gate": None,
            "notes": notes,
        }

    if (
        config.review_spam_low <= scores["spam_score"] <= config.review_spam_high
        and scores["operational_value_score"] >= 0.2
    ):
        return {
            "decision": "review",
            "spam_class": "unknown",
            "reasons": ["ambiguous_quality"],
            "hard_gate": None,
            "notes": notes,
        }

    if signals.boilerplate_ratio >= 0.7 and scores["operational_value_score"] < 0.25:
        return _gate("reject", "irrelevant_boilerplate", ["high_boilerplate_ratio"], "boilerplate")

    if (
        scores["quality_score"] >= config.quality_accept_min
        and scores["spam_score"] <= config.spam_accept_max
        and scores["operational_value_score"] >= config.operational_accept_min
    ):
        reasons.append("substantive_operational_content")
        if signals.reputation_score >= 0.7:
            reasons.append("authoritative_source")
        return {
            "decision": "accept",
            "spam_class": "clean",
            "reasons": reasons or ["substantive_operational_content"],
            "hard_gate": None,
            "notes": notes,
        }

    if scores["operational_value_score"] >= 0.3 and scores["spam_score"] < 0.45:
        return {
            "decision": "accept_with_penalty",
            "spam_class": "clean" if scores["spam_score"] < 0.3 else "unknown",
            "reasons": ["substantive_operational_content", "low_source_reputation"]
            if signals.reputation_score < 0.5
            else ["substantive_operational_content"],
            "hard_gate": None,
            "notes": notes,
        }

    if scores["spam_score"] >= 0.55:
        return {
            "decision": "quarantine",
            "spam_class": "suspicious",
            "reasons": ["ambiguous_quality"],
            "hard_gate": None,
            "notes": notes,
        }

    return {
        "decision": "review",
        "spam_class": "unknown",
        "reasons": ["ambiguous_quality"],
        "hard_gate": None,
        "notes": notes,
    }


def _gate(
    decision: FilterDecision,
    spam_class: str,
    reasons: list[str],
    hard_gate: str,
    notes: list[str] | None = None,
) -> dict:
    return {
        "decision": decision,
        "spam_class": spam_class,
        "reasons": reasons,
        "hard_gate": hard_gate,
        "notes": notes or [],
    }


def _is_stale(source: ValidatedSource, signals: QualitySignals, config: AntiSpamConfig) -> bool:
    if signals.stale_days is None:
        return False
    if source.source_type in {"authoritative_feed", "government", "open_data", "internal"}:
        limit = config.stale_authoritative_days
        if limit is None:
            return False
        return signals.stale_days > limit
    if source.source_type == "community":
        return signals.stale_days > config.stale_community_days
    return signals.stale_days > config.stale_news_days


def _apply_duplicate_gates(
    source: ValidatedSource,
    signals: QualitySignals,
    matches: list[DuplicateMatch],
    index: DuplicateIndex,
    tentative: dict,
) -> dict:
    """Reject same-source copies; leave cross-domain copies for syndication."""
    if tentative.get("hard_gate") in {"blocked_domain", "prompt_injection", "empty", "malformed"}:
        return tentative
    exact = [m for m in matches if m.kind in {"exact_hash", "rss_guid"}]
    url_dup = [m for m in matches if m.kind == "canonical_url"]
    near = [m for m in matches if m.kind == "near_duplicate"]
    if exact:
        prior = index.document(exact[0].source_id)
        if prior is None or not _different_domain(signals.domain, prior.domain):
            return _gate(
                "reject",
                "duplicate",
                ["exact_content_hash_match"],
                "exact_duplicate",
                notes=[f"duplicate_of:{exact[0].source_id}"],
            )
    if url_dup:
        prior = index.document(url_dup[0].source_id)
        if prior is None or not _different_domain(signals.domain, prior.domain):
            return _gate(
                "reject",
                "duplicate",
                ["canonical_url_match"],
                "url_duplicate",
                notes=[f"duplicate_of:{url_dup[0].source_id}"],
            )
    if near and not exact:
        prior = index.document(near[0].source_id)
        if prior is not None and not _different_domain(signals.domain, prior.domain):
            return _gate(
                "reject",
                "near_duplicate",
                ["near_duplicate_simhash"],
                "near_duplicate",
                notes=[f"duplicate_of:{near[0].source_id}"],
            )
    return tentative


def _different_domain(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return left != right


def _syndication(
    source: ValidatedSource,
    signals: QualitySignals,
    matches: list[DuplicateMatch],
    scores: dict[str, float],
    index: DuplicateIndex,
    tentative: dict,
) -> SyndicationInfo | None:
    if tentative["spam_class"] in {"duplicate"} and tentative["decision"] == "reject":
        match = next((m for m in matches if m.kind in {"exact_hash", "canonical_url", "rss_guid"}), None)
        if match:
            prior = index.document(match.source_id)
            if prior and prior.domain and signals.domain and prior.domain != signals.domain:
                cluster_id = f"syn-{match.source_id}"
                new_is_better = signals.reputation_score > prior.reputation_score + 0.05
                canonical = source.source_id if new_is_better else prior.source_id
                return SyndicationInfo(
                    cluster_id=cluster_id,
                    is_canonical=new_is_better,
                    canonical_source_id=canonical,
                    demotes_source_id=prior.source_id if new_is_better else None,
                    alternate_source_ids=[prior.source_id if new_is_better else source.source_id],
                    original_publisher=prior.publisher if not new_is_better else source.publisher,
                    match_method=match.method,
                )
        return None

    candidates = [
        m
        for m in matches
        if m.kind in {"syndication_candidate", "near_duplicate", "title_time", "exact_hash"}
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda m: m.probability)
    prior = index.document(best.source_id)
    if prior is None:
        return None
    different_domain = bool(prior.domain and signals.domain and prior.domain != signals.domain)
    if not different_domain and best.kind != "title_time":
        return None
    if scores["operational_value_score"] < 0.2 and signals.reputation_score < 0.5:
        return None
    cluster_id = index.canonical_of.get(f"syn-{prior.source_id}") or f"syn-{prior.source_id}"
    for cid, members in index.clusters.items():
        if prior.source_id in members or source.source_id in members:
            cluster_id = cid
            break
    existing_canonical = index.canonical_of.get(cluster_id, prior.source_id)
    existing_doc = index.document(existing_canonical) or prior
    new_is_better = signals.reputation_score > existing_doc.reputation_score + 0.05
    # Prefer configured wire domains as original publisher.
    if signals.domain and any(signals.domain == w or signals.domain.endswith("." + w) for w in ("reuters.com", "apnews.com", "ap.org", "afp.com")):
        new_is_better = True
    canonical = source.source_id if new_is_better else existing_canonical
    return SyndicationInfo(
        cluster_id=cluster_id,
        is_canonical=canonical == source.source_id,
        canonical_source_id=canonical,
        demotes_source_id=existing_canonical if new_is_better and existing_canonical != source.source_id else None,
        alternate_source_ids=[existing_canonical] if canonical == source.source_id else [source.source_id],
        original_publisher=source.publisher if new_is_better else existing_doc.publisher,
        match_method=best.method,
    )


def _eligibility(decision: FilterDecision, syndication: SyndicationInfo | None) -> tuple[bool, bool]:
    if decision == "accept":
        evidence, event = True, True
    elif decision == "accept_with_penalty":
        evidence, event = True, True
    else:
        evidence, event = False, False
    if syndication and not syndication.is_canonical:
        event = False
        if decision in {"accept", "accept_with_penalty"}:
            evidence = True
    return evidence, event


def _model_content(source: ValidatedSource, signals: QualitySignals) -> str:
    if source.html:
        return extract_text(source.html)
    return source.text


def _blend_model(
    decision: FilterDecision,
    spam_class: str,
    reasons: list[str],
    scores: dict[str, float],
    model: QualityModelOutput,
) -> tuple[FilterDecision, str, list[str], dict[str, float]]:
    new_decision = model.decision
    new_class = model.spam_class if model.spam_class else spam_class
    new_reasons = list(reasons)
    for token in model.reasons:
        if token not in new_reasons:
            new_reasons.append(token)
    if model.operational_facts_present:
        scores = dict(scores)
        scores["operational_value_score"] = round(
            clamp01(max(scores["operational_value_score"], 0.45)), 4
        )
        if "substantive_operational_content" not in new_reasons:
            new_reasons.append("substantive_operational_content")
        scores["quality_score"] = round(
            clamp01(0.7 * scores["quality_score"] + 0.3 * scores["operational_value_score"]),
            4,
        )
    if model.clickbait and new_class == "clean":
        new_class = "clickbait"
    if model.promotional_but_factual and new_decision == "accept":
        new_decision = "accept_with_penalty"
        if new_class == "clean":
            new_class = "promotional"
    if model.ai_generated_filler and not model.operational_facts_present:
        new_decision = "quarantine"
        new_class = "low_information"
    if new_decision == "review":
        new_decision = "quarantine"
    return new_decision, new_class, new_reasons, scores
