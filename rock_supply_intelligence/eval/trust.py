"""Benchmark trust / release-readiness. Incomplete or unlocked is never TRUSTED."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from rock_supply_intelligence.engine.timeutil import parse_utc
from rock_supply_intelligence.schemas.atomic import AtomicSample

ATOMIC_TARGET = 420
SCENARIO_TARGET = 28
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

SPLIT_TARGETS = {"dev": 120, "selection": 150, "holdout": 150}
CLASS_TARGETS = {
    "materially_relevant": 150,
    "monitor": 50,
    "irrelevant": 130,
    "ambiguous_conflicting": 50,
    "prompt_injection": 40,
}
LANGUAGE_TARGETS = {"en": 250, "zh-TW": 120, "mixed": 50}
EVENT_CATEGORY_TARGETS = {
    "weather_natural_disaster": 80,
    "port_vessel_carrier": 95,
    "labor_infrastructure_transportation": 70,
    "geopolitical_security": 60,
    "regulatory_trade_customs": 35,
    "irrelevant_general_world": 80,
}

FREEZE_EXCLUDED_DIRS = frozenset({"reports", "runs", "__pycache__", ".git"})
FREEZE_EXCLUDED_FILES = frozenset({"manifest.json", "tools/freeze_hash.py"})

TrustStatus = Literal["TRUSTED", "INCOMPLETE", "UNTRUSTED"]


class FrozenBenchmarkError(RuntimeError):
    """Locked benchmark inputs cannot be mutated in place."""


class BakeoffNotReadyError(RuntimeError):
    """Official bakeoff refused because the benchmark is not release-ready."""


class BenchmarkTrust(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TrustStatus
    release_ready: bool
    trusted: bool
    frozen: bool
    benchmark_version: str
    manifest_status: str
    unmet: list[str] = Field(default_factory=list)
    collected_samples: int
    target_samples: int = ATOMIC_TARGET
    expected_labels_reviewed: int
    tree_hash_recorded: str | None = None
    locked_at: str | None = None

    def banner(self) -> str:
        if self.trusted and self.frozen:
            return (
                f"Benchmark trust: TRUSTED / FROZEN ({self.benchmark_version}). "
                "Results may be compared as official bakeoff output."
            )
        return (
            f"Benchmark trust: {self.status} / NOT RELEASE-READY ({self.benchmark_version}). "
            "Results are draft/scaffold only. Open-scenario metric PASS does not mean "
            "the benchmark is frozen or trustworthy."
        )

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()

    def unmet_message(self, *, action: str) -> str:
        lines = [f"{action} refused: benchmark is not release-ready.", "Unmet requirements:"]
        lines.extend(f"- {item}" for item in self.unmet)
        return "\n".join(lines)


def freeze_tree_entries(benchmark_root: Path) -> dict[str, str]:
    root = Path(benchmark_root)
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in FREEZE_EXCLUDED_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative in FREEZE_EXCLUDED_FILES:
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def freeze_root_hash(entries: dict[str, str]) -> str:
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def load_manifest(benchmark_root: Path) -> dict[str, Any]:
    return json.loads((Path(benchmark_root) / "manifest.json").read_text())


def is_locked(benchmark_root: Path) -> bool:
    try:
        return load_manifest(benchmark_root).get("status") == "locked"
    except (OSError, json.JSONDecodeError):
        return False


def assert_benchmark_unlocked(benchmark_root: Path) -> None:
    if is_locked(benchmark_root):
        raise FrozenBenchmarkError(
            "Benchmark is locked. Do not mutate frozen inputs in place; create a new benchmark version."
        )


def _rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = parse_utc(value)
    if parsed is None:
        return False
    # Reject naive placeholders.
    if value.strip() in {"SET_BY_RELEASE_MANAGER", "null"}:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def count_collected_samples(benchmark_root: Path) -> tuple[int, Counter, Counter, Counter, Counter]:
    root = Path(benchmark_root)
    collected: list[AtomicSample] = []
    paths = list((root / "atomic").glob("*/*.json"))
    paths.extend((root / "holdout_sealed" / "atomic").glob("*/*.json"))
    for path in paths:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "sample_id" not in data:
            continue
        try:
            sample = AtomicSample.model_validate(data)
        except Exception:
            continue
        if sample.collection_status == "collected":
            collected.append(sample)
    return (
        len(collected),
        Counter(s.split for s in collected),
        Counter(s.labels.primary_class for s in collected),
        Counter(s.source.language for s in collected),
        Counter(s.labels.event_category for s in collected),
    )


def quota_shortfalls(
    split_counts: Counter,
    class_counts: Counter,
    lang_counts: Counter,
    cat_counts: Counter,
) -> list[str]:
    unmet: list[str] = []
    for kind, actual, targets in (
        ("split", split_counts, SPLIT_TARGETS),
        ("primary_class", class_counts, CLASS_TARGETS),
        ("language", lang_counts, LANGUAGE_TARGETS),
        ("event_category", cat_counts, EVENT_CATEGORY_TARGETS),
    ):
        for key, target in targets.items():
            got = int(actual.get(key, 0))
            if got < target:
                unmet.append(f"quota {kind} {key}: {got}/{target}")
    return unmet


def assess_trust_from_records(
    manifest: dict[str, Any],
    *,
    collected_count: int,
    split_counts: Counter,
    class_counts: Counter,
    lang_counts: Counter,
    cat_counts: Counter,
    current_tree_hash: str | None = None,
) -> BenchmarkTrust:
    unmet: list[str] = []
    completeness = manifest.get("completeness") or {}
    freeze = manifest.get("freeze") or {}
    review = manifest.get("label_review") or {}
    target = int(completeness.get("atomic_samples_target") or ATOMIC_TARGET)
    recorded_collected = completeness.get("atomic_samples_collected")
    reviewed_manifest = int(completeness.get("expected_atomic_labels_reviewed") or 0)
    reviewed_count = int(review.get("reviewed_count") if review.get("reviewed_count") is not None else reviewed_manifest)
    review_state = str(review.get("state") or "not_complete")
    tree_hash = freeze.get("tree_hash")
    locked_at = freeze.get("locked_at")
    manifest_status = str(manifest.get("status") or "")
    version = str(manifest.get("benchmark_version") or "unknown")

    if target != ATOMIC_TARGET:
        unmet.append(f"atomic target is {target}, required {ATOMIC_TARGET}")
    if collected_count < ATOMIC_TARGET:
        unmet.append(f"atomic corpus incomplete: {collected_count}/{ATOMIC_TARGET} collected")
    if recorded_collected != collected_count:
        unmet.append(
            f"manifest completeness.atomic_samples_collected={recorded_collected} "
            f"but collected files={collected_count}"
        )
    unmet.extend(quota_shortfalls(split_counts, class_counts, lang_counts, cat_counts))

    if review_state != "complete":
        unmet.append(f"expected-label review state is {review_state!r}, required complete")
    if reviewed_count != ATOMIC_TARGET or reviewed_manifest != ATOMIC_TARGET:
        unmet.append(
            f"expected atomic labels reviewed={reviewed_count} "
            f"(manifest {reviewed_manifest})/{ATOMIC_TARGET}"
        )
    if review_state == "complete" and not _rfc3339(review.get("completed_at")):
        unmet.append("label_review.completed_at is not a valid RFC 3339 timestamp")
    if review.get("reviewed_count") is not None and review.get("reviewed_count") != reviewed_manifest:
        unmet.append("label_review.reviewed_count does not match completeness.expected_atomic_labels_reviewed")

    hash_ok = isinstance(tree_hash, str) and bool(SHA256_RE.match(tree_hash))
    if not hash_ok:
        unmet.append("freeze tree_hash is missing")
    elif current_tree_hash and tree_hash != current_tree_hash:
        unmet.append("freeze tree_hash does not match current tree")

    if manifest_status != "locked":
        unmet.append(f"manifest status is {manifest_status!r}, required locked")
    if not _rfc3339(locked_at):
        unmet.append("freeze.locked_at is missing or not a valid RFC 3339 timestamp")

    corpus_incomplete = collected_count < ATOMIC_TARGET or any(u.startswith("quota ") for u in unmet)
    if not unmet:
        status: TrustStatus = "TRUSTED"
    elif corpus_incomplete or review_state != "complete" or reviewed_count != ATOMIC_TARGET:
        status = "INCOMPLETE"
    else:
        status = "UNTRUSTED"

    release_ready = not unmet and status == "TRUSTED"
    frozen = hash_ok and manifest_status == "locked" and _rfc3339(locked_at)
    return BenchmarkTrust(
        status=status,
        release_ready=release_ready,
        trusted=release_ready,
        frozen=bool(frozen and release_ready),
        benchmark_version=version,
        manifest_status=manifest_status,
        unmet=unmet,
        collected_samples=collected_count,
        target_samples=ATOMIC_TARGET,
        expected_labels_reviewed=reviewed_manifest,
        tree_hash_recorded=tree_hash if isinstance(tree_hash, str) else None,
        locked_at=locked_at if isinstance(locked_at, str) else None,
    )


def assess_trust(benchmark_root: Path, *, include_tree_hash: bool = True) -> BenchmarkTrust:
    root = Path(benchmark_root)
    manifest = load_manifest(root)
    collected, splits, classes, langs, cats = count_collected_samples(root)
    current = freeze_root_hash(freeze_tree_entries(root)) if include_tree_hash else None
    return assess_trust_from_records(
        manifest,
        collected_count=collected,
        split_counts=splits,
        class_counts=classes,
        lang_counts=langs,
        cat_counts=cats,
        current_tree_hash=current,
    )


def freeze_allowed(trust: BenchmarkTrust) -> list[str]:
    """Freeze may run only after corpus+quotas+label review. Hash/lock are freeze outputs."""
    return [
        item
        for item in trust.unmet
        if not item.startswith("freeze ")
        and "tree_hash" not in item
        and "manifest status" not in item
        and "locked_at" not in item
    ]


def require_official_bakeoff(benchmark_root: Path) -> BenchmarkTrust:
    trust = assess_trust(benchmark_root)
    if not trust.release_ready:
        raise BakeoffNotReadyError(trust.unmet_message(action="Official bakeoff"))
    return trust
