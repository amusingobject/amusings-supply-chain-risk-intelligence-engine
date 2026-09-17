"""Deterministic content, promotional, SEO, injection, and operational signals."""

from __future__ import annotations

import json
import re
from html import unescape

from rock_supply_intelligence.engine.antispam.duplicates import (
    canonicalize_url,
    normalize_title,
    sha256_text,
    simhash64,
    simhash_hex,
    tokenize,
)
from rock_supply_intelligence.engine.antispam.reputation import Reputation, host_of
from rock_supply_intelligence.engine.timeutil import parse_utc
from rock_supply_intelligence.schemas.source_quality import ContentKind, QualitySignals, ValidatedSource

SCRIPT_RE = re.compile(r"<script\b[^>]*>[\s\S]*?</script>", re.IGNORECASE)
STYLE_RE = re.compile(r"<style\b[^>]*>[\s\S]*?</style>", re.IGNORECASE)
NOSCRIPT_RE = re.compile(r"<noscript\b[^>]*>[\s\S]*?</noscript>", re.IGNORECASE)
NAV_RE = re.compile(r"<(nav|footer|header|aside)\b[^>]*>[\s\S]*?</\1>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
HTML_HINT_RE = re.compile(r"<(html|body|div|p|article|section|meta|link)\b", re.IGNORECASE)
TITLE_TAG_RE = re.compile(r"<title[^>]*>([\s\S]*?)</title>", re.IGNORECASE)
H1_RE = re.compile(r"<h1[^>]*>([\s\S]*?)</h1>", re.IGNORECASE)
HREF_RE = re.compile(r"""href\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
BODY_RE = re.compile(r"<body\b", re.IGNORECASE)
PDF_PLACEHOLDER_RE = re.compile(r"^\[PDF_UNEXTRACTED:")

PROMOTIONAL_RE = re.compile(
    r"\b(buy now|shop now|limited time|promo code|coupon|discount|sponsored|"
    r"advertorial|affiliate|add to cart|free trial|subscribe now|sign up today|"
    r"act now|deal of the day|click here to (buy|order|save)|order now|"
    r"best price|% off|save \d+%|lead gen|request a quote|book a demo)\b",
    re.IGNORECASE,
)
AFFILIATE_HREF_RE = re.compile(
    r"(amazon\.[a-z.]+/.+|tag=|affid=|affiliate|clickbank|shareasale|"
    r"impact\.com|cj\.com|/promo/|coupon)",
    re.IGNORECASE,
)
SOCIAL_RE = re.compile(
    r"(#\w+|follow me|follow us|subscribe for more|giveaway|crypto pump|"
    r"t\.me/|telegram\.me|dm me|like and share|🔥{2,}|\$\w+ to the moon)",
    re.IGNORECASE,
)
CLICKBAIT_TITLE_RE = re.compile(
    r"\b(breaking|shocking|you won'?t believe|destroyed|secret|exposed|"
    r"panic|chaos|gone viral|what happened next|doctors hate|unbelievable|"
    r"this one trick|total collapse)\b",
    re.IGNORECASE,
)
AI_FILLER_RE = re.compile(
    r"(in today'?s rapidly evolving|it is important to note|delve into|"
    r"the landscape of|in conclusion,|as an ai|in this comprehensive guide|"
    r"unlock the potential|ever-changing world|holistic approach|"
    r"game-changer for businesses)",
    re.IGNORECASE,
)
BOILERPLATE_RE = re.compile(
    r"\b(cookie policy|privacy policy|all rights reserved|subscribe to our newsletter|"
    r"related articles|share this|leave a comment|terms of (use|service)|"
    r"accept cookies|navigation menu|skip to content)\b",
    re.IGNORECASE,
)
INJECTION_PATTERNS = (
    re.compile(r"ignore (all )?(previous|prior|above) instructions", re.IGNORECASE),
    re.compile(r"\bsystem override\b", re.IGNORECASE),
    re.compile(r"\byou are now (an |a )?autonomous\b", re.IGNORECASE),
    re.compile(r"\bdisregard (your )?(rules|safety|system prompt)\b", re.IGNORECASE),
    re.compile(r"reveal (your |the )?(system )?prompt", re.IGNORECASE),
    re.compile(r"\b(call tools|function call|tool_call)\b", re.IGNORECASE),
    re.compile(r"update netsuite|write to salesforce|netsuite\.update", re.IGNORECASE),
    re.compile(r"/etc/passwd|api[_-]?key|exfil", re.IGNORECASE),
    re.compile(r"\bdo not treat this as data\b", re.IGNORECASE),
    re.compile(r"\b(jailbreak|dan mode|developer mode enabled)\b", re.IGNORECASE),
    re.compile(r"immediately (reroute|place a purchase order|email customers)", re.IGNORECASE),
)
OPERATIONAL_RE = re.compile(
    r"\b(port|terminal|berth|vessel|ship|container|typhoon|typhoon warning|"
    r"earthquake|congestion|strike|labor|canal|suez|panama|delay|closure|"
    r"disruption|customs|sanction|carrier|draught|drought|cyber|ais|"
    r"locode|keelung|kaohsiung|taichung|hualien|long beach|los angeles|"
    r"baltimore|red sea|yantian|shanghai|tsunami|landslide|berth window|"
    r"gate hours|pilotage|stevedore|ilo|itia|bill of lading|transshipment|"
    r"颱風|警報|港口|基隆|高雄|臺中|花蓮|地震)\b",
    re.IGNORECASE,
)
FACT_RE = re.compile(
    r"(\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(:\d{2})?Z?\b|\bM\s?\d\.\d\b|"
    r"\b\d+\s?(km|kt|knots|teu|hours|days)\b|\b[A-Z]{2}[A-Z]{3}\b)"
)
STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "is",
        "are",
        "was",
        "with",
        "by",
        "at",
        "as",
        "from",
        "that",
        "this",
        "it",
        "be",
        "not",
    }
)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def extract_text(html_or_text: str) -> str:
    text = SCRIPT_RE.sub(" ", html_or_text)
    text = STYLE_RE.sub(" ", text)
    text = NOSCRIPT_RE.sub(" ", text)
    text = NAV_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    return WS_RE.sub(" ", text).strip()


def extract_title(html: str | None, fallback: str | None) -> str | None:
    if html:
        match = TITLE_TAG_RE.search(html)
        if match:
            title = extract_text(match.group(1))
            if title:
                return title
        match = H1_RE.search(html)
        if match:
            title = extract_text(match.group(1))
            if title:
                return title
    return fallback


def detect_kind(source: ValidatedSource) -> ContentKind:
    raw = source.html or source.text or ""
    stripped = raw.strip()
    if not stripped:
        return "empty"
    if PDF_PLACEHOLDER_RE.match(stripped):
        return "pdf_placeholder"
    if "\x00" in stripped[:2000]:
        return "binary"
    if stripped[0] in "{[":
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass
    if stripped.startswith("<?xml") or stripped.startswith("<rss") or stripped.startswith("<feed"):
        return "xml"
    if source.html or HTML_HINT_RE.search(stripped[:8000]):
        return "html"
    ctype = (source.content_type or "").lower()
    if "html" in ctype:
        return "html"
    if "json" in ctype:
        return "json"
    if "xml" in ctype or "rss" in ctype:
        return "xml"
    return "text"


def _malformed_html(html: str) -> bool:
    if "\x00" in html:
        return True
    opens = html.count("<")
    closes = html.count(">")
    if opens and abs(opens - closes) / max(opens, 1) > 0.25 and opens > 20:
        return True
    if HTML_HINT_RE.search(html) and not BODY_RE.search(html) and "<html" in html.lower():
        return True
    replacement = html.count("\ufffd")
    if replacement > 50 and replacement / max(len(html), 1) > 0.02:
        return True
    return False


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n{2,}|(?<=\.)\s{2,}", text) if p.strip()]
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if len(p.strip()) > 40]
    return parts


def _unique_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def _keyword_stuffing(tokens: list[str]) -> float:
    content = [t for t in tokens if t not in STOPWORDS and not t.isdigit()]
    if len(content) < 20:
        return 0.0
    counts: dict[str, int] = {}
    for tok in content:
        counts[tok] = counts.get(tok, 0) + 1
    top = max(counts.values()) / len(content)
    return clamp01((top - 0.08) / 0.20)


def _prompt_injection_score(text: str) -> float:
    hits = 0
    weight = 0.0
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            hits += 1
            weight += 0.22
    if hits >= 2:
        weight += 0.2
    if re.search(r"SYSTEM\s*:", text[:400]):
        weight += 0.25
    return clamp01(weight)


def _stale_days(source: ValidatedSource, as_of: str | None) -> float | None:
    published = parse_utc(source.published_at or source.effective_at or source.observed_at)
    ref = parse_utc(as_of or source.retrieved_at)
    if published is None or ref is None:
        return None
    delta = (ref - published).total_seconds() / 86400.0
    return max(0.0, delta)


def extract_signals(
    source: ValidatedSource,
    reputation: Reputation,
    as_of: str | None = None,
) -> QualitySignals:
    html = source.html
    raw = html if html is not None else source.text
    kind = detect_kind(source)
    if kind == "html" and html is None:
        html = source.text
        raw = html

    extracted = source.text or ""
    if kind == "html" and html:
        extracted = extract_text(html)
    elif kind in {"json", "xml"}:
        extracted = source.text or raw
    elif kind == "empty":
        extracted = ""
    elif not extracted:
        extracted = extract_text(raw) if raw else ""

    title = extract_title(html, source.title)
    if not title:
        title = extracted[:120] if extracted else source.source_name

    tokens = tokenize(extracted)
    unique_ratio = _unique_token_ratio(tokens)
    paragraphs = _paragraphs(extracted)
    unique_paras = len({p.lower() for p in paragraphs}) if paragraphs else 0
    repeated_ratio = 0.0
    if paragraphs:
        repeated_ratio = 1.0 - (unique_paras / len(paragraphs))

    html_to_text = None
    malformed = False
    missing_body = False
    if kind == "html" and html:
        html_len = max(len(html), 1)
        html_to_text = len(extracted) / html_len
        malformed = _malformed_html(html)
        missing_body = not BODY_RE.search(html) and len(extracted) < 80
    if kind == "empty":
        missing_body = True
    if kind == "binary":
        malformed = True

    hrefs = HREF_RE.findall(html or "") if kind == "html" else []
    affiliate_hits = sum(1 for h in hrefs if AFFILIATE_HREF_RE.search(h))
    affiliate_ratio = affiliate_hits / max(len(hrefs), 1) if hrefs else 0.0

    promo_hits = len(PROMOTIONAL_RE.findall(extracted + " " + (title or "")))
    promotional = clamp01(promo_hits / 4.0 + min(0.5, affiliate_ratio * 1.2))
    if re.search(r"\bsponsored\b|\badvertorial\b", extracted, re.IGNORECASE):
        promotional = clamp01(promotional + 0.35)

    boilerplate_hits = len(BOILERPLATE_RE.findall(extracted))
    boilerplate_ratio = clamp01(boilerplate_hits / 8.0)
    if html_to_text is not None and html_to_text < 0.08 and kind == "html":
        boilerplate_ratio = max(boilerplate_ratio, clamp01(1.0 - html_to_text * 8))

    seo = _keyword_stuffing(tokens)
    if repeated_ratio > 0.5:
        seo = max(seo, clamp01(repeated_ratio))
    if unique_ratio < 0.08 and len(tokens) >= 40:
        seo = max(seo, 0.9)
    heading_count = len(re.findall(r"<h[1-3]\b", html or "", re.IGNORECASE))
    if kind == "html" and heading_count > 25 and len(extracted) < 4000:
        seo = max(seo, 0.55)

    social = 0.0
    social_hits = len(SOCIAL_RE.findall(extracted))
    if social_hits:
        social = clamp01(social_hits / 5.0)
    if kind == "text" and len(extracted) < 280 and social_hits:
        social = max(social, 0.7)

    clickbait = 0.0
    headline_support = None
    title_l = title or ""
    if CLICKBAIT_TITLE_RE.search(title_l):
        clickbait = 0.55
    title_tokens = [t for t in tokenize(title_l) if t not in STOPWORDS]
    if title_tokens and extracted:
        overlap = sum(1 for t in title_tokens if t in extracted.lower())
        headline_support = overlap / len(title_tokens)
        if headline_support < 0.35 and CLICKBAIT_TITLE_RE.search(title_l):
            clickbait = max(clickbait, 0.75)
        elif headline_support < 0.25 and len(title_tokens) >= 4:
            clickbait = max(clickbait, 0.4)

    ai_filler = clamp01(len(AI_FILLER_RE.findall(extracted)) / 4.0)

    ops_hits = len(OPERATIONAL_RE.findall(extracted))
    fact_hits = len(FACT_RE.findall(extracted))
    density = clamp01(ops_hits / 6.0)
    if unique_ratio < 0.2 and len(tokens) >= 30:
        density *= unique_ratio / 0.2
    if social >= 0.5:
        density *= 0.25
    if promotional >= 0.7:
        density *= 0.45
    density = clamp01(density)
    structured = 0.0
    if kind in {"json", "xml"}:
        structured = 0.85 if fact_hits or ops_hits else 0.55
    elif fact_hits >= 3 and ops_hits >= 2 and unique_ratio >= 0.25:
        structured = clamp01(0.3 + 0.1 * min(fact_hits, 5))

    injection = _prompt_injection_score((title or "") + "\n" + extracted + "\n" + (source.text or "")[:2000])

    canonical = canonicalize_url(source.source_locator)
    content_hash = source.content_hash or sha256_text(raw or extracted)
    fingerprint = simhash64(extracted if len(extracted) >= 40 else (raw or ""))

    if kind in {"json", "xml"}:
        boilerplate_ratio = min(boilerplate_ratio, 0.15)
        seo = min(seo, 0.2)

    return QualitySignals(
        content_kind=kind,
        char_count=len(raw or ""),
        extracted_char_count=len(extracted),
        token_count=len(tokens),
        unique_token_ratio=round(unique_ratio, 4),
        boilerplate_ratio=round(boilerplate_ratio, 4),
        repeated_paragraph_ratio=round(clamp01(repeated_ratio), 4),
        html_to_text_ratio=None if html_to_text is None else round(html_to_text, 4),
        malformed_markup=malformed,
        missing_body=missing_body,
        promotional_score=round(promotional, 4),
        affiliate_link_ratio=round(clamp01(affiliate_ratio), 4),
        seo_score=round(seo, 4),
        social_spam_score=round(social, 4),
        clickbait_score=round(clickbait, 4),
        ai_filler_score=round(ai_filler, 4),
        headline_body_support=None if headline_support is None else round(headline_support, 4),
        operational_keyword_density=round(density, 4),
        structured_fact_score=round(structured, 4),
        prompt_injection_score=round(injection, 4),
        stale_days=_stale_days(source, as_of),
        reputation_tier=reputation.tier,
        reputation_score=reputation.score,
        domain=reputation.domain or host_of(source.source_locator),
        canonical_url=canonical,
        content_sha256=content_hash,
        simhash=simhash_hex(fingerprint),
        title_normalized=normalize_title(title),
    )
