#!/usr/bin/env python3
"""Fail-closed source-index discovery for registry proposal generation.

Discovery indexes are used only to find direct publisher pages. They are never
used as benchmark evidence and cannot materialize an atomic fixture. A proposed
page must be explicitly added to the versioned source registry before the
bounded collector can fetch, hash, quarantine, and materialize it.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import registry_collect as registry
from collect_osint import fetch, utc_now

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS = ROOT / "reports" / "registry-discovery-proposals.json"


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            label = " ".join(" ".join(self._text).split())
            self.links.append((self._href, label))
            self._href = None
            self._text = []


def plain_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    return " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", text)).split())


def extract_links(index_url: str, body: bytes) -> list[tuple[str, str]]:
    parser = AnchorParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return [(urljoin(index_url, href), label) for href, label in parser.links]


def direct_url_allowed(url: str, source: dict[str, Any], prefixes: list[str]) -> bool:
    parsed = urlparse(url)
    domain = source["domain"].lower()
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == domain or host.endswith("." + domain)):
        return False
    if not any(parsed.path.startswith(prefix) for prefix in prefixes):
        return False
    lowered = url.lower()
    return not any(token in lowered for token in ("/search?", "documents.json?", "conditions%5bterm%5d"))


def profile_url_allowed(url: str, source: dict[str, Any], profile: dict[str, Any]) -> bool:
    path = urlparse(url).path
    return (
        direct_url_allowed(url, source, profile["path_prefixes"])
        and not any(path.startswith(prefix) for prefix in profile.get("exclude_path_prefixes", []))
        and len([part for part in path.split("/") if part]) >= profile.get("min_path_segments", 1)
    )


def url_date_matches(url: str, published_at: str) -> bool:
    match = re.search(
        r"/([12]\d{3})/(january|february|march|april|may|june|july|august|september|october|november|december)(?:/|$)",
        url,
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    expected_month = datetime.strptime(match.group(2).lower(), "%B").month
    actual = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return actual.year == int(match.group(1)) and actual.month == expected_month


def metadata(body: bytes) -> tuple[str, str | None, str]:
    decoded = body.decode("utf-8", errors="replace")
    text = plain_text(body)
    article_title_match = re.search(
        r"(?is)<h[1-3][^>]*class=[\"'][^\"']*\b(?:article-title|page-title|title)\b[^\"']*[\"'][^>]*>(.*?)</h[1-3]>",
        decoded,
    )
    title_match = article_title_match or re.search(r"(?is)<meta[^>]+(?:property|name)=[\"'](?:og:title|twitter:title)[\"'][^>]+content=[\"']([^\"']+)", decoded)
    if not title_match:
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", decoded)
    title = " ".join(html.unescape(title_match.group(1)).split()) if title_match else ""
    article_match = re.search(r"(?is)<article\b[^>]*>(.*?)</article>", decoded)
    article_html = article_match.group(1) if article_match else ""
    article_text = plain_text(article_html.encode("utf-8")) if article_html else ""
    date_match = re.search(r"(?i)datetime=[\"']([12]\d{3}-\d{2}-\d{2})", article_html)
    if not date_match:
        date_match = re.search(r"(?i)(?:published_time|datepublished)[^>]{0,200}?([12]\d{3}-\d{2}-\d{2})", decoded)
    if not date_match:
        date_match = re.search(r"(?:發布日期|Published)\s*[:：]?\s*([12]\d{3}[-/]\d{1,2}[-/]\d{1,2})", text, flags=re.IGNORECASE)
    if not date_match and article_text:
        natural_date_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+([12]\d{3})\b",
            article_text,
            flags=re.IGNORECASE,
        )
        if natural_date_match:
            try:
                date = datetime.strptime(natural_date_match.group(0), "%B %d, %Y").replace(tzinfo=timezone.utc)
                return title, date.isoformat().replace("+00:00", "Z"), text
            except ValueError:
                pass
    if not date_match:
        return title, None, text
    try:
        date = datetime.fromisoformat(date_match.group(1).replace("/", "-")).replace(tzinfo=timezone.utc)
    except ValueError:
        return title, None, text
    return title, date.isoformat().replace("+00:00", "Z"), text


def score(template: dict[str, Any], deficits: dict[str, dict[str, int]]) -> int:
    return sum(
        deficits[kind].get(value, 0)
        for kind, value in (
            ("primary_class", template["primary_class"]),
            ("language", template["language"]),
            ("event_category", template["event_category"]),
        )
    )


def proposal_for_page(source: dict[str, Any], profile: dict[str, Any], url: str, body: bytes, deficits: dict[str, dict[str, int]]) -> dict[str, Any] | None:
    if not profile_url_allowed(url, source, profile):
        return None
    title, published_at, text = metadata(body)
    lowered = text.lower()
    terms = profile["include_terms"] + profile["candidate_template"]["accept_terms"]
    if not all(term.lower() in lowered for term in terms):
        return None
    if not title or not published_at:
        return None
    if profile.get("not_before") and published_at < profile["not_before"]:
        return None
    if profile.get("require_url_date_match") and not url_date_matches(url, published_at):
        return None
    template = profile["candidate_template"]
    return {
        "status": "requires_registry_approval",
        "source_id": source["source_id"],
        "profile_id": profile["profile_id"],
        "url": url,
        "title": title,
        "published_at": published_at,
        "suggested_candidate": template,
        "quota_score": score(template, deficits),
        "notes": "Discovery proposal only; direct page was checked for configured terms. Add a stable sample ID to the versioned registry before collection.",
    }


def discover(limit: int = 50, source_ids: set[str] | None = None) -> dict[str, Any]:
    data = registry.load_registry()
    available_source_ids = {source["source_id"] for source in data["sources"]}
    unknown_source_ids = (source_ids or set()) - available_source_ids
    if unknown_source_ids:
        raise ValueError(f"unknown discovery source_id(s): {', '.join(sorted(unknown_source_ids))}")
    deficits = registry.quota_snapshot(registry.active_samples())
    known_urls = {candidate["url"] for source in data["sources"] for candidate in source["candidates"]}
    proposals: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source in data["sources"]:
        if source_ids is not None and source["source_id"] not in source_ids:
            continue
        config = source.get("discovery")
        if not source["enabled"] or not config:
            continue
        per_index = config.get("max_links_per_index", 25)
        for index_url in config["index_urls"]:
            if not direct_url_allowed(index_url, source, [urlparse(index_url).path]):
                continue
            try:
                links = [
                    row for row in extract_links(index_url, fetch(index_url))
                    if any(direct_url_allowed(row[0], source, profile["path_prefixes"]) for profile in config["profiles"])
                ][:per_index]
            except Exception:
                continue
            for url, _ in links:
                if url in known_urls or url in seen_urls:
                    continue
                for profile in config["profiles"]:
                    if not profile_url_allowed(url, source, profile):
                        continue
                    try:
                        proposal = proposal_for_page(source, profile, url, fetch(url), deficits)
                    except Exception:
                        proposal = None
                    if proposal:
                        proposals.append(proposal)
                        seen_urls.add(url)
                        break
                    if len(proposals) >= limit:
                        break
                if len(proposals) >= limit:
                    break
            if len(proposals) >= limit:
                break
    proposals.sort(key=lambda item: (-item["quota_score"], item["source_id"], item["url"]))
    return {"generated_at": utc_now(), "registry_id": data["registry_id"], "deficits": deficits, "proposals": proposals[:limit]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--source", action="append", dest="sources", help="Discover one approved source_id; may be repeated")
    parser.add_argument("--output", type=Path, default=PROPOSALS)
    args = parser.parse_args()
    result = discover(limit=args.limit, source_ids=set(args.sources) if args.sources else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
