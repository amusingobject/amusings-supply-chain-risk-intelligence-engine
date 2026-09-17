"""Configurable source-reputation lookup.

Reputation is a prior, not a fact. Unknown domains stay unknown rather than
being treated as authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from rock_supply_intelligence.engine.antispam.config import AntiSpamConfig
from rock_supply_intelligence.schemas.source_quality import ReputationTier, ValidatedSource

TIER_SCORE: dict[str, float] = {
    "very_high": 0.96,
    "high": 0.86,
    "moderate_high": 0.74,
    "moderate": 0.58,
    "low": 0.36,
    "very_low": 0.16,
    "blocked": 0.0,
    "unknown": 0.48,
}

# Host suffix → tier. Longest suffix wins.
DOMAIN_TIERS: dict[str, ReputationTier] = {
    "usgs.gov": "very_high",
    "cwa.gov.tw": "very_high",
    "rdc28.cwa.gov.tw": "very_high",
    "noaa.gov": "very_high",
    "nhc.noaa.gov": "very_high",
    "weather.gov": "very_high",
    "faa.gov": "very_high",
    "navcen.uscg.gov": "very_high",
    "treasury.gov": "very_high",
    "ofac.treasury.gov": "very_high",
    "twport.com.tw": "very_high",
    "kaohsiungport.gov.tw": "very_high",
    "motc.gov.tw": "very_high",
    "tsunami.gov": "very_high",
    "gdacs.org": "high",
    "reliefweb.int": "high",
    "reuters.com": "high",
    "apnews.com": "high",
    "ap.org": "high",
    "afp.com": "high",
    "bloomberg.com": "high",
    "bbc.com": "high",
    "bbc.co.uk": "high",
    "ft.com": "high",
    "wsj.com": "high",
    "nytimes.com": "high",
    "theguardian.com": "high",
    "aljazeera.com": "high",
    "nikkei.com": "high",
    "scmp.com": "high",
    "joc.com": "moderate_high",
    "lloydslist.com": "moderate_high",
    "freightwaves.com": "moderate_high",
    "gcaptain.com": "moderate_high",
    "maritime-executive.com": "moderate_high",
    "container-news.com": "moderate_high",
    "seatrade-maritime.com": "moderate_high",
    "maersk.com": "very_high",
    "msc.com": "very_high",
    "cma-cgm.com": "very_high",
    "evergreen-line.com": "very_high",
    "hapag-lloyd.com": "very_high",
    "one-line.com": "very_high",
    "yangming.com": "very_high",
    "hmm21.com": "very_high",
}

AUTHORITY_TIERS: dict[str, ReputationTier] = {
    "official_government": "very_high",
    "official_port": "very_high",
    "official_port_authority": "very_high",
    "carrier_api": "very_high",
    "intergovernmental": "high",
    "wire_service": "high",
    "reputable_media": "high",
    "industry_publication": "moderate_high",
    "none": "unknown",
}

RELIABILITY_TIERS: dict[str, ReputationTier] = {
    "very_high": "very_high",
    "high": "high",
    "medium": "moderate",
    "moderate": "moderate",
    "low": "low",
    "very_low": "very_low",
    "not_applicable": "unknown",
}


@dataclass(frozen=True)
class Reputation:
    tier: ReputationTier
    score: float
    domain: str | None
    basis: tuple[str, ...]


def host_of(locator: str | None) -> str | None:
    if not locator:
        return None
    text = locator.strip()
    if "://" not in text:
        return None
    host = (urlparse(text).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _suffix_tier(host: str, table: dict[str, str]) -> str | None:
    best: str | None = None
    best_len = -1
    for suffix, tier in table.items():
        if host == suffix or host.endswith("." + suffix):
            if len(suffix) > best_len:
                best = tier
                best_len = len(suffix)
    return best


def _rank(tier: str) -> int:
    order = {
        "blocked": 0,
        "very_low": 1,
        "low": 2,
        "unknown": 3,
        "moderate": 4,
        "moderate_high": 5,
        "high": 6,
        "very_high": 7,
    }
    return order.get(tier, 3)


def lookup_reputation(source: ValidatedSource, config: AntiSpamConfig) -> Reputation:
    host = host_of(source.source_locator)
    bases: list[str] = []
    tier: str = "unknown"

    extra = {k.lower(): v for k, v in config.extra_domain_tiers.items()}
    if host:
        blocked = _suffix_tier(host, {d: "blocked" for d in config.blocked_domains})
        farm = _suffix_tier(host, {d: "very_low" for d in config.content_farm_domains})
        extra_hit = _suffix_tier(host, extra) if extra else None
        catalog = _suffix_tier(host, DOMAIN_TIERS)
        if blocked:
            return Reputation("blocked", 0.0, host, ("blocked_domain",))
        if extra_hit:
            tier = extra_hit
            bases.append("configured_domain")
        if catalog and _rank(catalog) > _rank(tier):
            tier = catalog
            bases.append("domain_catalog")
        if farm and _rank(farm) < _rank(tier):
            tier = farm
            bases.append("content_farm_domain")
        if _suffix_tier(host, {d: "high" for d in config.wire_domains}) and _rank("high") > _rank(tier):
            tier = "high"
            bases.append("wire_domain")
        if _suffix_tier(host, {d: "moderate_high" for d in config.industry_domains}):
            if _rank("moderate_high") > _rank(tier):
                tier = "moderate_high"
                bases.append("industry_domain")

    authority = (source.source_authority or "").strip().lower()
    if authority in AUTHORITY_TIERS:
        auth_tier = AUTHORITY_TIERS[authority]
        if _rank(auth_tier) > _rank(tier):
            tier = auth_tier
            bases.append("source_authority")

    reliability = (source.source_reliability or "").strip().lower()
    if reliability in RELIABILITY_TIERS and reliability != "not_applicable":
        rel_tier = RELIABILITY_TIERS[reliability]
        if _rank(rel_tier) > _rank(tier):
            tier = rel_tier
            bases.append("source_reliability")

    if source.source_type in {"authoritative_feed", "government", "open_data"} and _rank(tier) < _rank("high"):
        # Type is a prior, not proof of a specific agency.
        if host and _suffix_tier(host, DOMAIN_TIERS):
            pass
        elif authority in AUTHORITY_TIERS:
            pass
        else:
            if _rank("moderate_high") > _rank(tier):
                tier = "moderate_high"
                bases.append("source_type_prior")
    if source.source_type in {"internal", "analyst"} and _rank(tier) < _rank("high"):
        tier = "high"
        bases.append("internal_or_analyst")
    if source.source_type == "community" and _rank(tier) > _rank("moderate"):
        # Do not automatically promote community posts.
        pass
    elif source.source_type == "community" and tier == "unknown":
        tier = "low"
        bases.append("community_prior")
    if source.source_type == "news" and tier == "unknown" and not host:
        tier = "moderate"
        bases.append("news_unhosted")

    if not bases:
        bases.append("unknown_source")

    resolved: ReputationTier = tier  # type: ignore[assignment]
    return Reputation(resolved, TIER_SCORE[resolved], host, tuple(bases))
