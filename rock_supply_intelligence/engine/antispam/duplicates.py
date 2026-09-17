"""Exact and near-duplicate detection. Never uses an LLM."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rock_supply_intelligence.engine.antispam.config import TRACKING_QUERY_KEYS

TOKEN_RE = re.compile(r"[a-z0-9\u4e00-\u9fff]{2,}", re.IGNORECASE)
TITLE_SUFFIX_RE = re.compile(
    r"\s*[-–—|:]\s*(reuters|ap|associated press|afp|bloomberg|bbc|cnn|nytimes|"
    r"the guardian|financial times|wsj|south china morning post)\s*$",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s\u4e00-\u9fff]+", re.UNICODE)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if not raw or "://" not in raw:
        return raw.lower().rstrip("/") or None
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_QUERY_KEYS
    ]
    query_pairs.sort()
    query = urlencode(query_pairs, doseq=True)
    scheme = (parsed.scheme or "https").lower()
    netloc = host
    if parsed.port and parsed.port not in {80, 443}:
        netloc = f"{host}:{parsed.port}"
    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    text = TITLE_SUFFIX_RE.sub("", title)
    text = PUNCT_RE.sub(" ", text.lower())
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def simhash64(text: str) -> int:
    tokens = tokenize(text)
    if not tokens:
        return 0
    weights: dict[str, int] = {}
    for tok in tokens:
        weights[tok] = weights.get(tok, 0) + 1
    acc = [0] * 64
    for tok, weight in weights.items():
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        h = int.from_bytes(digest[:8], "big")
        for bit in range(64):
            acc[bit] += weight if (h >> bit) & 1 else -weight
    fingerprint = 0
    for bit in range(64):
        if acc[bit] >= 0:
            fingerprint |= 1 << bit
    return fingerprint


def hamming64(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def simhash_hex(value: int) -> str:
    return f"{value:016x}"


@dataclass(frozen=True)
class IndexedDocument:
    source_id: str
    content_sha256: str
    canonical_url: str | None
    title_normalized: str | None
    simhash: int
    domain: str | None
    publisher: str | None
    published_at: str | None
    source_type: str
    reputation_score: float
    rss_guid: str | None = None


@dataclass
class DuplicateMatch:
    kind: str
    source_id: str
    probability: float
    hamming: int | None = None
    method: str = ""


@dataclass
class DuplicateIndex:
    """In-memory duplicate / syndication index for one ingest run or process."""

    by_hash: dict[str, str] = field(default_factory=dict)
    by_url: dict[str, str] = field(default_factory=dict)
    by_rss: dict[str, str] = field(default_factory=dict)
    by_title_time: dict[str, str] = field(default_factory=dict)
    documents: list[IndexedDocument] = field(default_factory=list)
    clusters: dict[str, list[str]] = field(default_factory=dict)
    canonical_of: dict[str, str] = field(default_factory=dict)

    def lookup(
        self,
        *,
        content_sha256: str,
        canonical_url: str | None,
        title_normalized: str | None,
        published_at: str | None,
        simhash: int,
        rss_guid: str | None,
        near_dup_hamming: int,
        syndication_hamming: int,
    ) -> list[DuplicateMatch]:
        hits: list[DuplicateMatch] = []
        exact = self.by_hash.get(content_sha256)
        if exact:
            hits.append(
                DuplicateMatch(
                    kind="exact_hash",
                    source_id=exact,
                    probability=1.0,
                    method="sha256",
                )
            )
        if canonical_url and canonical_url in self.by_url:
            hits.append(
                DuplicateMatch(
                    kind="canonical_url",
                    source_id=self.by_url[canonical_url],
                    probability=0.99,
                    method="canonical_url",
                )
            )
        if rss_guid and rss_guid in self.by_rss:
            hits.append(
                DuplicateMatch(
                    kind="rss_guid",
                    source_id=self.by_rss[rss_guid],
                    probability=0.98,
                    method="rss_guid",
                )
            )
        title_key = _title_time_key(title_normalized, published_at)
        if title_key and title_key in self.by_title_time:
            hits.append(
                DuplicateMatch(
                    kind="title_time",
                    source_id=self.by_title_time[title_key],
                    probability=0.9,
                    method="title_timestamp",
                )
            )
        if simhash:
            for doc in self.documents:
                if doc.simhash == 0:
                    continue
                dist = hamming64(simhash, doc.simhash)
                if dist <= near_dup_hamming:
                    hits.append(
                        DuplicateMatch(
                            kind="near_duplicate",
                            source_id=doc.source_id,
                            probability=max(0.7, 1.0 - dist / 16.0),
                            hamming=dist,
                            method="simhash",
                        )
                    )
                elif dist <= syndication_hamming:
                    hits.append(
                        DuplicateMatch(
                            kind="syndication_candidate",
                            source_id=doc.source_id,
                            probability=max(0.45, 1.0 - dist / 20.0),
                            hamming=dist,
                            method="simhash",
                        )
                    )
        return hits

    def register(self, doc: IndexedDocument) -> None:
        self.documents.append(doc)
        self.by_hash.setdefault(doc.content_sha256, doc.source_id)
        if doc.canonical_url:
            self.by_url.setdefault(doc.canonical_url, doc.source_id)
        if doc.rss_guid:
            self.by_rss.setdefault(doc.rss_guid, doc.source_id)
        title_key = _title_time_key(doc.title_normalized, doc.published_at)
        if title_key:
            self.by_title_time.setdefault(title_key, doc.source_id)

    def document(self, source_id: str) -> IndexedDocument | None:
        for doc in self.documents:
            if doc.source_id == source_id:
                return doc
        return None


def _title_time_key(title: str | None, published_at: str | None) -> str | None:
    if not title or len(title) < 12:
        return None
    day = (published_at or "")[:10]
    if len(day) != 10:
        return None
    return f"{day}|{title[:80]}"
