#!/usr/bin/env python3
"""Registry-driven, quota-aware, fail-closed public-source collector."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from rock_supply_intelligence.eval.trust import CLASS_TARGETS, EVENT_CATEGORY_TARGETS, LANGUAGE_TARGETS, SPLIT_TARGETS, count_collected_samples
from rock_supply_intelligence.schemas.atomic import AtomicSample
from collect_osint import fetch, utc_now
from materialize_atomic import update_counts

REGISTRY = ROOT / "collection-source-registry.json"
SCHEMA = ROOT / "schemas/collection-source-registry.schema.json"
STATE = ROOT / "reports/collection-registry-state.json"
CACHE = ROOT / "reports/collection-candidate-cache.json"
HEALTH = ROOT / "reports/collection-health.json"
QUARANTINE = ROOT / "quarantine/candidates"
RAW_QUARANTINE = ROOT / "quarantine/raw"
RAW = ROOT / "raw/registry-wave3"
RUNS = ROOT / "reports/collection-runs"
LOCK = ROOT / "reports/collection-registry.lock"
PLAN_ID = "RSIB-registry-wave3"
COLLECTOR_VERSION = "registry-collector/1.0.0"


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text()) if path.is_file() else default


def load_registry() -> dict[str, Any]:
    registry = load_json(REGISTRY, {})
    schema = load_json(SCHEMA, {})
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(registry), key=lambda e: list(e.path))
    if errors:
        raise ValueError("invalid source registry: " + "; ".join(error.message for error in errors[:5]))
    ids = [c["sample_id"] for s in registry["sources"] for c in s["candidates"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate sample_id in source registry")
    return registry


def active_samples() -> list[AtomicSample]:
    samples: list[AtomicSample] = []
    for path in sorted((ROOT / "atomic").rglob("*.json")):
        data = load_json(path, {})
        if isinstance(data, dict) and data.get("sample_id") and data.get("collection_status") == "collected":
            samples.append(AtomicSample.model_validate(data))
    return samples


def existing_ids() -> set[str]:
    result = {s.sample_id for s in active_samples()}
    for base in (ROOT / "rejected/atomic", ROOT / "holdout_sealed/atomic"):
        if base.exists():
            result.update(path.stem for path in base.rglob("ATOM-*.json"))
    return result


def quota_snapshot(samples: list[AtomicSample]) -> dict[str, dict[str, int]]:
    # Reuse the benchmark's deterministic counter so sealed holdout records are
    # represented in aggregate scheduling without exposing them to discovery or
    # any model path.
    _, split_counts, class_counts, lang_counts, cat_counts = count_collected_samples(ROOT)
    actual = {"split": split_counts, "primary_class": class_counts, "language": lang_counts, "event_category": cat_counts}
    targets = {"split": SPLIT_TARGETS, "primary_class": CLASS_TARGETS, "language": LANGUAGE_TARGETS, "event_category": EVENT_CATEGORY_TARGETS}
    return {kind: {key: max(0, target - actual[kind].get(key, 0)) for key, target in target_map.items()} for kind, target_map in targets.items()}


def discover(limit: int = 0, write: bool = True, ignore_cooldown: bool = False) -> dict[str, Any]:
    registry = load_registry()
    samples = active_samples()
    sample_by_id = {sample.sample_id: sample for sample in samples}
    ids = existing_ids()
    deficits = quota_snapshot(samples)
    state = load_json(STATE, {"candidates": {}})
    working_split_deficits = dict(deficits["split"])
    candidates: list[dict[str, Any]] = []
    for source in registry["sources"]:
        if not source["enabled"]:
            continue
        for declared in source["candidates"]:
            prior = state.get("candidates", {}).get(declared["sample_id"], {})
            retry_after = prior.get("retry_after")
            cooling = bool(not ignore_cooldown and retry_after and retry_after > utc_now())
            status = "already_present" if declared["sample_id"] in ids else "cooldown" if cooling else "ready"
            split = declared.get("preferred_split", "auto")
            if split == "auto":
                existing = sample_by_id.get(declared["sample_id"])
                if existing is not None:
                    split = existing.split
                else:
                    split = max(working_split_deficits, key=lambda key: (working_split_deficits[key], key))
                    if status == "ready":
                        working_split_deficits[split] = max(0, working_split_deficits[split] - 1)
            score = sum([
                deficits["primary_class"].get(declared["primary_class"], 0),
                deficits["event_category"].get(declared["event_category"], 0),
                deficits["language"].get(declared["language"], 0),
                deficits["split"].get(split, 0),
            ])
            candidates.append({**declared, "split": split, "source_id": source["source_id"], "publisher": source["publisher"], "domain": source["domain"], "license": source.get("license"), "access_constraints": source.get("access_constraints"), "rate_limit_s": source["rate_limit_s"], "max_retries": source["max_retries"], "score": score, "status": status})
    candidates.sort(key=lambda c: (c["status"] != "ready", -c["score"], c["sample_id"]))
    ready = [c for c in candidates if c["status"] == "ready"]
    if limit:
        ready = ready[:limit]
    payload = {"generated_at": utc_now(), "registry_id": registry["registry_id"], "deficits": deficits, "ready": ready, "all_candidates": candidates}
    if write:
        atomic_write(CACHE, payload)
    return payload


def validate_url(candidate: dict[str, Any]) -> str | None:
    parsed = urlparse(candidate["url"])
    host = (parsed.hostname or "").lower(); expected = candidate["domain"].lower()
    if parsed.scheme != "https" or not (host == expected or host.endswith("." + expected)):
        return "url_domain_not_approved"
    lowered = candidate["url"].lower()
    if any(token in lowered for token in ("/search?", "documents.json?", "conditions%5bterm%5d")):
        return "search_result_url_forbidden"
    published = datetime.fromisoformat(candidate["published_at"].replace("Z", "+00:00"))
    if published > datetime.now(timezone.utc):
        return "future_publication_date"
    return None


def is_pdf(body: bytes, url: str) -> bool:
    return body.startswith(b"%PDF") or urlparse(url).path.lower().endswith(".pdf")


def extracted_text(body: bytes, url: str) -> str:
    if is_pdf(body, url):
        if not body.startswith(b"%PDF") or not shutil.which("pdftotext"):
            return ""
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.pdf"; source.write_bytes(body)
            proc = subprocess.run(["pdftotext", "-layout", str(source), "-"], capture_output=True, check=False, timeout=60)
            return proc.stdout.decode("utf-8", errors="replace")
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", text))


def validate_payload(candidate: dict[str, Any], body: bytes, known_hashes: set[str]) -> tuple[str | None, str]:
    digest = hashlib.sha256(body).hexdigest()
    if digest in known_hashes:
        return "duplicate_content_hash", digest
    if len(body) < 200:
        return "payload_too_small", digest
    text = " ".join(extracted_text(body, candidate["url"]).lower().split())
    if not text:
        return "unextractable_payload", digest
    missing = [term for term in candidate["accept_terms"] if term.lower() not in text]
    if missing:
        return "accept_terms_missing", digest
    return None, digest


def quarantine(candidate: dict[str, Any], reason: str, body: bytes | None, digest: str | None) -> None:
    record = {"sample_id": candidate["sample_id"], "source_id": candidate["source_id"], "url": candidate["url"], "reason": reason, "observed_at": utc_now(), "content_hash": digest}
    if body is not None:
        RAW_QUARANTINE.mkdir(parents=True, exist_ok=True)
        raw = RAW_QUARANTINE / f"{candidate['sample_id']}.bin"; raw.write_bytes(body)
        record["raw_ref"] = raw.relative_to(ROOT).as_posix()
    atomic_write(QUARANTINE / f"{candidate['sample_id']}.json", record)


def materialize(candidate: dict[str, Any], body: bytes, digest: str) -> Path:
    suffix = ".pdf" if is_pdf(body, candidate["url"]) else ".html"
    RAW.mkdir(parents=True, exist_ok=True); raw = RAW / f"{candidate['sample_id']}{suffix}"; raw.write_bytes(body)
    source_type = "news" if candidate["source_id"].startswith("ilwu") else "government"
    sample = {
        "sample_id": candidate["sample_id"], "schema_version": "0.1", "split": candidate["split"], "collection_status": "collected",
        "source": {"source_id": candidate["source_id"], "source_type": source_type, "publisher": candidate["publisher"], "source_name": candidate["title"], "source_authority": "primary_organization", "source_reliability": "high", "source_locator": candidate["url"], "language": candidate["language"], "content_type": "application/pdf" if suffix == ".pdf" else "text/html", "retrieved_at": utc_now(), "published_at": candidate["published_at"], "raw_ref": raw.relative_to(ROOT).as_posix(), "content_hash": digest, "hash_method": "sha256", "license": candidate.get("license"), "access_constraints": candidate.get("access_constraints")},
        "labels": {"primary_class": candidate["primary_class"], "primary_label": "registry_provisional", "event_category": candidate["event_category"], "event_type": candidate["event_type"], "event_subtype": candidate["source_id"], "expected_relevance_class": candidate["primary_class"], "expected_disposition": candidate["expected_disposition"], "tasks": ["relevance", "event_extraction", "grounding"]},
        "provenance": {"collection_plan_id": PLAN_ID, "collector_id": "rock-supply-intelligence", "collector_version": COLLECTOR_VERSION, "ingestion_method": "registry_direct_https_get", "pipeline_run_id": f"{PLAN_ID}-{utc_now()}", "transformations": [], "ai_used": False, "synthetic": False, "content_status": "lawful_capture", "adjudication_status": "provisional", "notes": "Registry-selected direct primary source; provisional label requires human review."}
    }
    AtomicSample.model_validate(sample)
    dest = ROOT / "atomic" / candidate["split"] / f"{candidate['sample_id']}.json"; atomic_write(dest, sample)
    return dest


def write_review_packet(collected: list[dict[str, Any]], stamp: str) -> str | None:
    if not collected:
        return None
    path = ROOT / "reports" / f"human-review-registry-{stamp}.md"
    lines = [
        "# Registry Collection Human Review",
        "",
        "Status: human-review worksheet only. These items remain provisional until decisions are recorded.",
        "",
        "## What to review",
        "",
        "For each item, decide whether the retained direct source genuinely supports the proposed narrow class and category. Do not determine whether a particular shipment, supplier, vessel, product, or transaction is affected.",
        "",
        "Use **Keep**, **Relabel**, **Reject**, or **Escalate**. Keep means the source supports the proposed evidence label; it does not authorize an operational or legal decision.",
        "",
        "| ID | Proposed label | What the source must establish | Direct source |",
        "| --- | --- | --- | --- |",
    ]
    for row in collected:
        c = row["candidate"]
        cue = "; ".join(c["accept_terms"])
        title = c["title"].replace("|", "\\|")
        lines.append(
            f"| `{c['sample_id']}` | `{c['primary_class']} / {c['event_category']}` | "
            f"{title}; verify cues: {cue} | [primary source]({c['url']}) |"
        )
    lines.extend(
        [
            "",
            "## Reply format",
            "",
            "Reply with `Keep all` or list per-ID exceptions, for example: `Keep ATOM-...; Relabel ATOM-... to monitor; Escalate ATOM-...`.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def run(limit: int, retry_now: bool = False, sample_ids: list[str] | None = None) -> dict[str, Any]:
    """Run one collector process at a time.

    Split allocation and raw-file materialization share mutable state, so a
    second process must fail before discovery rather than race the active run.
    The advisory lock is released automatically if the process exits.
    """
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("collector already running; retry after the active run completes") from exc
        return _run_locked(limit, retry_now=retry_now, sample_ids=sample_ids)


def select_ready(plan: dict[str, Any], limit: int, sample_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Select only explicitly requested ready candidates when IDs are supplied."""
    ready = plan["ready"]
    if not sample_ids:
        return ready[:limit]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("requested sample_id values must be unique")
    ready_by_id = {candidate["sample_id"]: candidate for candidate in ready}
    unavailable = [sample_id for sample_id in sample_ids if sample_id not in ready_by_id]
    if unavailable:
        raise ValueError(f"requested sample_id(s) not ready: {', '.join(unavailable)}")
    if len(sample_ids) > limit:
        raise ValueError("requested sample_id count exceeds --limit")
    return [ready_by_id[sample_id] for sample_id in sample_ids]


def _run_locked(limit: int, retry_now: bool = False, sample_ids: list[str] | None = None) -> dict[str, Any]:
    from rock_supply_intelligence.eval.trust import assert_benchmark_unlocked
    assert_benchmark_unlocked(ROOT)
    plan = discover(write=True, ignore_cooldown=retry_now)
    plan["ready"] = select_ready(plan, limit, sample_ids)
    state = load_json(STATE, {"version": 1, "candidates": {}, "sources": {}})
    state.setdefault("candidates", {})
    state.setdefault("sources", {})
    known_hashes = {s.source.content_hash for s in active_samples() if s.source.content_hash}
    collected: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for candidate in plan["ready"]:
        reason = validate_url(candidate)
        if reason:
            quarantine(candidate, reason, None, None)
            failed.append({"sample_id": candidate["sample_id"], "reason": reason})
            _record_failure(state, candidate, reason)
            checkpoint_state(state)
            continue
        body = None; error = None
        for attempt in range(candidate["max_retries"] + 1):
            try:
                body = fetch(candidate["url"]); error = None; break
            except Exception as exc:
                error = type(exc).__name__
                if attempt < candidate["max_retries"]:
                    time.sleep(min(8, 2 ** attempt))
        if body is None:
            reason = f"fetch_failed:{error}"
            quarantine(candidate, reason, None, None)
            failed.append({"sample_id": candidate["sample_id"], "reason": reason})
            _record_failure(state, candidate, reason)
            checkpoint_state(state)
            continue
        reason, digest = validate_payload(candidate, body, known_hashes)
        if reason:
            quarantine(candidate, reason, body, digest)
            failed.append({"sample_id": candidate["sample_id"], "reason": reason})
            _record_failure(state, candidate, reason)
            checkpoint_state(state)
            continue
        path = materialize(candidate, body, digest)
        known_hashes.add(digest)
        collected.append({"candidate": candidate, "path": str(path), "content_hash": digest})
        state["candidates"][candidate["sample_id"]] = {"status": "collected", "collected_at": utc_now(), "content_hash": digest}
        state["sources"][candidate["source_id"]] = {"last_checked_at": utc_now(), "last_sample_id": candidate["sample_id"]}
        checkpoint_state(state)
        time.sleep(candidate["rate_limit_s"])
    checkpoint_state(state)
    count, raw_count = update_counts()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {"generated_at": utc_now(), "registry_id": plan["registry_id"], "collected": [{k:v for k,v in row.items() if k != "candidate"} | {"sample_id":row["candidate"]["sample_id"]} for row in collected], "failed": failed, "corpus_collected": count, "raw_bodies_retained": raw_count}
    result["review_packet"] = write_review_packet(collected, stamp); atomic_write(RUNS / f"registry-run-{stamp}.json", result); write_health(result, discover(write=True))
    return result


def _record_failure(state: dict[str, Any], candidate: dict[str, Any], reason: str) -> None:
    prior = state["candidates"].get(candidate["sample_id"], {}); attempts = int(prior.get("attempts", 0)) + 1
    retry_after = datetime.now(timezone.utc) + timedelta(minutes=min(24 * 60, 30 * (2 ** (attempts - 1))))
    state["candidates"][candidate["sample_id"]] = {"status": "failed", "attempts": attempts, "last_error": reason, "last_attempt_at": utc_now(), "retry_after": retry_after.replace(microsecond=0).isoformat().replace("+00:00", "Z")}
    state["sources"][candidate["source_id"]] = {"last_checked_at": utc_now(), "last_sample_id": candidate["sample_id"], "last_error": reason}


def checkpoint_state(state: dict[str, Any]) -> None:
    """Atomically persist progress after every candidate for crash-safe resumes."""
    state["updated_at"] = utc_now()
    atomic_write(STATE, state)


def write_health(result: dict[str, Any], plan: dict[str, Any]) -> None:
    history = load_json(HEALTH, {"version": 1, "runs": []})
    history["runs"].append(
        {
            "generated_at": result["generated_at"],
            "collected": len(result["collected"]),
            "failed": len(result["failed"]),
            "failure_reasons": dict(Counter(item["reason"] for item in result["failed"])),
        }
    )
    history["runs"] = history["runs"][-50:]
    refresh_health(history, plan, result["corpus_collected"])


def refresh_health(history: dict[str, Any] | None = None, plan: dict[str, Any] | None = None, corpus_count: int | None = None) -> dict[str, Any]:
    """Refresh current health without fetching sources or adding a run record."""
    history = history or load_json(HEALTH, {"version": 1, "runs": []})
    plan = plan or discover(write=True)
    registry = load_registry()
    state = load_json(STATE, {"candidates": {}, "sources": {}})
    state.setdefault("sources", {})
    candidate_sources = {
        candidate["sample_id"]: source["source_id"]
        for source in registry["sources"]
        for candidate in source["candidates"]
    }
    for sample_id, candidate_state in state.get("candidates", {}).items():
        source_id = candidate_sources.get(sample_id)
        observed_at = candidate_state.get("collected_at") or candidate_state.get("last_attempt_at")
        if source_id and observed_at and source_id not in state["sources"]:
            state["sources"][source_id] = {"last_checked_at": observed_at, "last_sample_id": sample_id}
    checkpoint_state(state)
    if corpus_count is None:
        corpus_count = count_collected_samples(ROOT)[0]
    statuses = Counter(candidate["status"] for candidate in plan["all_candidates"])
    history["current"] = {
        "generated_at": utc_now(),
        "corpus_collected": corpus_count,
        "ready_candidates": len(plan["ready"]),
        "candidate_statuses": dict(statuses),
        "enabled_sources": sum(1 for source in registry["sources"] if source["enabled"]),
        "disabled_sources": sum(1 for source in registry["sources"] if not source["enabled"]),
        "source_cursors": state.get("sources", {}),
        "deficits": plan["deficits"],
    }
    atomic_write(HEALTH, history)
    return history


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("--limit", type=int, default=0)
    r = sub.add_parser("run"); r.add_argument("--limit", type=int, default=10); r.add_argument("--retry-now", action="store_true"); r.add_argument("--sample-id", action="append", dest="sample_ids")
    sub.add_parser("health")
    args = parser.parse_args()
    if args.command == "plan": result = discover(limit=args.limit)
    elif args.command == "run": result = run(args.limit, retry_now=args.retry_now, sample_ids=args.sample_ids)
    else: result = refresh_health()
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
