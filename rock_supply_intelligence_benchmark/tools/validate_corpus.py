#!/usr/bin/env python3
"""Validate canonical schemas, manifests, hashes, provenance, splits, and quotas.

Does not modify ground-truth labels.

Release path: --strict-quotas / --release fails when 420-sample quotas are unmet.
Collection-progress path: --collection-progress reports quota shortfalls as warnings
and must not be used for freeze, bakeoff-readiness, or trusted-result workflows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, SchemaError

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from pydantic import ValidationError

from rock_supply_intelligence.eval.trust import (
    ATOMIC_TARGET,
    CLASS_TARGETS,
    EVENT_CATEGORY_TARGETS,
    LANGUAGE_TARGETS,
    SPLIT_TARGETS,
    assess_trust,
)
from rock_supply_intelligence.schemas.atomic import AtomicSample

REQUIRED_PATHS = [
    "README.md",
    "VERSION",
    "manifest.json",
    "schemas",
    "atomic/dev",
    "atomic/selection",
    "atomic/holdout",
    "scenarios/dev",
    "scenarios/selection",
    "scenarios/holdout",
    "raw",
    "expected",
    "scoring",
    "reports",
]
REQUIRED_SCHEMAS = [
    "benchmark-manifest.schema.json",
    "atomic-osint-sample.schema.json",
    "scenario-manifest.schema.json",
    "evidence-record.schema.json",
]

_SCHEMA_VALIDATORS: dict[str, Draft202012Validator] = {}



def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, f"{path.relative_to(ROOT)}: invalid JSON: {exc}"


def validate_json_schema(report: "Report", path: Path, data: object, schema_name: str) -> None:
    """Validate an instance with the versioned JSON Schema contract.

    Pydantic models remain useful runtime conveniences; this check makes the
    published benchmark schemas executable release contracts as well.
    """
    try:
        validator = _SCHEMA_VALIDATORS.get(schema_name)
        if validator is None:
            schema, err = load_json(ROOT / "schemas" / schema_name)
            if err:
                report.error(err)
                return
            if not isinstance(schema, dict):
                report.error(f"schemas/{schema_name}: schema is not an object")
                return
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            _SCHEMA_VALIDATORS[schema_name] = validator
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            report.error(
                f"{path.relative_to(ROOT)}: {schema_name} violation at {location}: {error.message}"
            )
    except SchemaError as exc:
        report.error(f"schemas/{schema_name}: invalid JSON Schema: {exc.message}")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.info.append(msg)


def validate_structure(report: Report) -> None:
    for name in REQUIRED_PATHS:
        if not (ROOT / name).exists():
            report.error(f"missing required path: {name}")
    for name in REQUIRED_SCHEMAS:
        if not (ROOT / "schemas" / name).is_file():
            report.error(f"missing required schema: {name}")


def validate_all_json_syntax(report: Report) -> None:
    for path in ROOT.rglob("*.json"):
        if "__pycache__" in path.parts:
            continue
        _, err = load_json(path)
        if err:
            report.error(err)


def validate_scenarios(report: Report, strict_quotas: bool) -> list[dict]:
    index, err = load_json(ROOT / "scenarios/index.json")
    if err:
        report.error(err)
        return []
    actual: list[dict] = []
    for split in ("dev", "selection", "holdout"):
        paths = list((ROOT / "scenarios" / split).glob("*.json"))
        sealed = ROOT / "holdout_sealed" / "scenarios" / split
        if sealed.exists():
            paths.extend(sealed.glob("*.json"))
        for path in sorted(paths):
            item, err = load_json(path)
            if err:
                report.error(err)
                continue
            if not isinstance(item, dict):
                report.error(f"{path}: scenario manifest is not an object")
                continue
            validate_json_schema(report, path, item, "scenario-manifest.schema.json")
            actual.append(item)
            parent = path.parent.name
            if item.get("split") != parent:
                report.error(f"{path.name}: split={item.get('split')} but directory={parent}")
            required = [
                "scenario_id",
                "scenario_version",
                "split",
                "evaluation_timestamp",
                "canonical_contract",
                "historical_anchor",
                "evidence",
                "synthetic_business_state",
                "expected",
                "scoring_metadata",
            ]
            for key in required:
                if key not in item:
                    report.error(f"{path.name}: missing {key}")
            eval_ts = item.get("evaluation_timestamp")
            for ev in item.get("evidence") or []:
                # Scenario evidence is a fixture-link record, not the runtime
                # canonical Evidence contract. The latter has lifecycle fields
                # (created_at/updated_at) produced by normalization and must
                # not be imposed on historical scenario manifests here.
                if not isinstance(ev, dict):
                    report.error(f"{path.name}: scenario evidence entry is not an object")
                    continue
                if ev.get("content_hash") is None and ev.get("collection_status") == "collected":
                    report.error(f"{path.name}: collected evidence missing hash")
                if ev.get("collection_status") == "collected" and eval_ts:
                    from rock_supply_intelligence.eval.e2e import evidence_available_at

                    if not evidence_available_at(ev, eval_ts):
                        report.error(f"{path.name}: evidence {ev.get('id')} not available at {eval_ts}")
                if ev.get("source_name") == "TO_BE_COLLECTED" or ev.get("excerpt_or_payload_path") == "TO_BE_COLLECTED":
                    report.warn(f"{path.name}: placeholder evidence remains")
                raw_ref = ev.get("raw_ref")
                if ev.get("collection_status") == "collected" and raw_ref:
                    raw_path = ROOT / raw_ref
                    sealed_raw = ROOT / "holdout_sealed" / raw_ref
                    if not raw_path.exists() and not sealed_raw.exists():
                        report.error(f"{path.name}: missing raw evidence {raw_ref}")
            _validate_source_claim_compatibility(report, path, item, strict_quotas)
    ids = [x.get("scenario_id") for x in actual]
    if len(actual) != 28:
        report.error(f"expected 28 scenario manifests, got {len(actual)}")
    if len(set(ids)) != len(ids):
        report.error(f"duplicate scenario IDs: {[i for i,c in Counter(ids).items() if c>1]}")
    split_counts = Counter(x.get("split") for x in actual)
    if split_counts != {"dev": 8, "selection": 10, "holdout": 10}:
        report.error(f"wrong scenario split counts: {dict(split_counts)}")
    if isinstance(index, dict) and len(index.get("scenarios") or []) != 28:
        report.error("scenarios/index.json completeness mismatch")
    collected_evidence = 0
    for item in actual:
        for ev in item.get("evidence") or []:
            if ev.get("collection_status") == "collected":
                collected_evidence += 1
    report.note(f"scenario manifests: {len(actual)}; collected evidence records: {collected_evidence}")
    return actual


def _validate_source_claim_compatibility(
    report: Report, path: Path, scenario: dict, strict_quotas: bool
) -> None:
    """Prevent weather or synthetic evidence from silently proving port operations.

    A port closure, restriction, reopening, or carrier-service assertion needs
    evidence that explicitly declares operational-claim support.  This is a
    gate, not a classifier: absence of that declaration requires human review.
    """
    anchor = scenario.get("historical_anchor") or {}
    title = str(anchor.get("title") or "").lower()
    expected = scenario.get("expected") or {}
    external = expected.get("external_event") or {}
    event_type = str(external.get("event_type") or anchor.get("event_type") or "").lower()
    operational_words = ("port", "terminal", "closure", "closed", "restriction", "reopen", "carrier")
    requires_operational_support = (
        event_type in {"port_disruption", "port_congestion", "carrier_exception"}
        or any(word in title for word in operational_words)
    )
    if not requires_operational_support:
        return
    collected = [ev for ev in scenario.get("evidence") or [] if ev.get("collection_status") == "collected"]
    support = {
        str(claim).lower()
        for ev in collected
        for claim in (ev.get("supported_claims") or [])
    }
    required = {"port_operations", "carrier_service", event_type}
    if support & required:
        return
    weather_only = [
        str(ev.get("source_name") or "")
        for ev in collected
        if "weather" in str(ev.get("source_name") or "").lower()
        or "typhoon" in str(ev.get("source_name") or "").lower()
    ]
    detail = "weather-only evidence" if weather_only else "no declared operational-claim support"
    msg = (
        f"{path.name}: operational claim requires source supported_claims containing "
        f"port_operations, carrier_service, or {event_type!r}; found {detail}"
    )
    (report.error if strict_quotas else report.warn)(msg)


def load_atomic_samples(report: Report) -> list[tuple[Path, AtomicSample]]:
    samples: list[tuple[Path, AtomicSample]] = []
    paths = list((ROOT / "atomic").glob("*/*.json"))
    paths.extend((ROOT / "holdout_sealed" / "atomic").glob("*/*.json"))
    for path in sorted(paths):
        data, err = load_json(path)
        if err:
            report.error(err)
            continue
        if not isinstance(data, dict) or "sample_id" not in data:
            report.error(f"{path.relative_to(ROOT)}: not an atomic sample manifest")
            continue
        validate_json_schema(report, path, data, "atomic-osint-sample.schema.json")
        try:
            sample = AtomicSample.model_validate(data)
        except ValidationError as exc:
            report.error(f"{path.relative_to(ROOT)}: schema invalid: {exc}")
            continue
        if sample.split != path.parent.name:
            report.error(f"{sample.sample_id}: split={sample.split} but directory={path.parent.name}")
        samples.append((path, sample))
    return samples


def validate_atomic(report: Report, samples: list[tuple[Path, AtomicSample]], strict_quotas: bool) -> None:
    ids = [s.sample_id for _, s in samples]
    dupes = [i for i, c in Counter(ids).items() if c > 1]
    if dupes:
        report.error(f"duplicate atomic sample_id: {dupes}")

    collected = [s for _, s in samples if s.collection_status == "collected"]
    synthetic = [s for s in collected if s.provenance.synthetic]
    reviewed = [s for s in collected if s.provenance.adjudication_status == "reviewed"]
    release_eligible = [s for s in reviewed if not s.provenance.synthetic]
    for path, sample in samples:
        src = sample.source
        if sample.collection_status == "collected":
            if src.content_hash is None:
                report.error(f"{sample.sample_id}: collected sample missing content_hash")
            if src.retrieved_at is None:
                report.error(f"{sample.sample_id}: collected sample missing retrieved_at")
            raw_path = ROOT / src.raw_ref
            sealed_raw = ROOT / "holdout_sealed" / src.raw_ref
            if not raw_path.is_file() and sealed_raw.is_file():
                raw_path = sealed_raw
            if not raw_path.is_file():
                report.error(f"{sample.sample_id}: missing raw file {src.raw_ref}")
            elif src.content_hash:
                actual = sha256(raw_path)
                if actual != src.content_hash:
                    report.error(
                        f"{sample.sample_id}: hash mismatch listed={src.content_hash} actual={actual}"
                    )
            if sample.provenance.content_status == "metadata_only":
                report.error(f"{sample.sample_id}: collected but content_status=metadata_only")
            if "synthetic" not in sample.provenance.model_dump():
                report.error(f"{sample.sample_id}: missing provenance.synthetic")
        if sample.labels.expected_relevance_class and sample.labels.expected_relevance_class != sample.labels.primary_class:
            report.warn(
                f"{sample.sample_id}: expected_relevance_class={sample.labels.expected_relevance_class} "
                f"!= primary_class={sample.labels.primary_class}"
            )
        if sample.labels.primary_class == "prompt_injection" and not sample.provenance.synthetic:
            report.warn(f"{sample.sample_id}: prompt_injection sample is not marked synthetic")

    # Orphan raw files
    manifested_raw = {s.source.raw_ref for _, s in samples}
    # Human-reviewed removals retain their original manifests and raw bytes in
    # rejected/ for audit. Those raw files are therefore intentional, not
    # collection orphans.
    for path in (ROOT / "rejected" / "atomic").rglob("*.json"):
        data, err = load_json(path)
        if err:
            report.error(err)
        elif isinstance(data, dict):
            raw_ref = (data.get("source") or {}).get("raw_ref")
            if isinstance(raw_ref, str):
                manifested_raw.add(raw_ref)
    for path in (ROOT / "raw").rglob("*"):
        if not path.is_file() or path.name in {"README.md", ".gitkeep"}:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if (
            rel.startswith("raw/e2e-synthetic/")
            or rel.startswith("holdout_sealed/raw/e2e-synthetic/")
            or rel.startswith("raw/scenario-grounding/")
        ):
            continue
        if rel not in manifested_raw:
            report.warn(f"raw file has no sample manifest: {rel}")

    split_counts = Counter(s.split for s in collected)
    class_counts = Counter(s.labels.primary_class for s in collected)
    lang_counts = Counter(s.source.language for s in collected)
    cat_counts = Counter(s.labels.event_category for s in collected)

    def _quota(kind: str, actual: Counter, targets: dict[str, int]) -> None:
        for key, target in targets.items():
            got = actual.get(key, 0)
            msg = f"{kind} {key}: {got}/{target}"
            if got < target:
                (report.error if strict_quotas else report.warn)(f"quota shortfall {msg}")
            else:
                report.note(f"quota met {msg}")

    report.note(f"atomic manifests: {len(samples)}; collected: {len(collected)}")
    report.note(
        "inventory: retained=%d; synthetic=%d; adjudicated=%d; release_eligible=%d"
        % (len(collected), len(synthetic), len(reviewed), len(release_eligible))
    )
    report.note(f"collected split counts: {dict(split_counts)}")
    report.note(f"collected class counts: {dict(class_counts)}")
    report.note(f"collected language counts: {dict(lang_counts)}")
    report.note(f"collected event_category counts: {dict(cat_counts)}")
    _quota("split", split_counts, SPLIT_TARGETS)
    _quota("primary_class", class_counts, CLASS_TARGETS)
    _quota("language", lang_counts, LANGUAGE_TARGETS)
    _quota("event_category", cat_counts, EVENT_CATEGORY_TARGETS)

    corpus, err = load_json(ROOT / "atomic/corpus_manifest.json")
    if err:
        report.error(err)
        return
    if not isinstance(corpus, dict):
        report.error("corpus_manifest.json is not an object")
        return
    if corpus.get("target_samples") != 420:
        report.error(f"corpus target_samples={corpus.get('target_samples')} expected 420")
    recorded = corpus.get("collected_samples")
    if recorded != len(collected):
        report.error(
            f"corpus_manifest collected_samples={recorded} but {len(collected)} collected manifests exist"
        )
    top, err = load_json(ROOT / "manifest.json")
    if err:
        report.error(err)
        return
    if isinstance(top, dict):
        completeness = top.get("completeness") or {}
        if completeness.get("atomic_samples_collected") != len(collected):
            report.error(
                "manifest.json completeness.atomic_samples_collected="
                f"{completeness.get('atomic_samples_collected')} but collected={len(collected)}"
            )
        raw_bodies = sum(
            1
            for p in list((ROOT / "raw").rglob("*")) + list((ROOT / "holdout_sealed" / "raw").rglob("*"))
            if p.is_file()
            and p.name not in {"README.md", ".gitkeep"}
            and "scenario-grounding" not in p.relative_to(ROOT).parts
        )
        if completeness.get("raw_bodies_retained") != raw_bodies:
            report.error(
                "manifest.json completeness.raw_bodies_retained="
                f"{completeness.get('raw_bodies_retained')} but files={raw_bodies}"
            )
        if completeness.get("atomic_samples_target") != ATOMIC_TARGET:
            report.error(
                f"manifest.json completeness.atomic_samples_target="
                f"{completeness.get('atomic_samples_target')} expected {ATOMIC_TARGET}"
            )
        review = top.get("label_review") or {}
        manifest_reviewed = completeness.get("expected_atomic_labels_reviewed")
        if manifest_reviewed != len(reviewed):
            # The manifest summary must be derived from active fixture state,
            # not manually claimed. `reviewed` includes synthetic fixtures;
            # release_eligible is intentionally non-synthetic only.
            report.error(
                "manifest.json completeness.expected_atomic_labels_reviewed="
                f"{manifest_reviewed} but reviewed active manifests={len(reviewed)}"
            )
        if review.get("reviewed_count") is not None and review.get("reviewed_count") != manifest_reviewed:
            report.error(
                "label_review.reviewed_count does not match completeness.expected_atomic_labels_reviewed"
            )
        if top.get("status") == "locked" and completeness.get("atomic_samples_collected") != ATOMIC_TARGET:
            report.error("benchmark is locked but atomic corpus is not complete")
        if top.get("status") == "locked" and (review.get("state") or "not_complete") != "complete":
            report.error("benchmark is locked but expected-label review is not complete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-quotas",
        "--release",
        action="store_true",
        dest="strict_quotas",
        help="release validation: fail if 420-sample quotas are unmet",
    )
    parser.add_argument(
        "--collection-progress",
        action="store_true",
        help="non-release collection progress: quota shortfalls are warnings only",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    if args.strict_quotas and args.collection_progress:
        print("ERROR: --strict-quotas/--release cannot be combined with --collection-progress")
        return 2
    report = Report()
    validate_structure(report)
    validate_all_json_syntax(report)
    validate_scenarios(report, strict_quotas=args.strict_quotas)
    samples = load_atomic_samples(report)
    validate_atomic(report, samples, strict_quotas=args.strict_quotas)
    payload = {
        "ok": not report.errors,
        "errors": report.errors,
        "warnings": report.warnings,
        "info": report.info,
        "collected_samples": sum(1 for _, s in samples if s.collection_status == "collected"),
        "atomic_manifests": len(samples),
        "inventory": {
            "retained": sum(1 for _, s in samples if s.collection_status == "collected"),
            "synthetic": sum(1 for _, s in samples if s.collection_status == "collected" and s.provenance.synthetic),
            "adjudicated": sum(1 for _, s in samples if s.collection_status == "collected" and s.provenance.adjudication_status == "reviewed"),
            "release_eligible": sum(1 for _, s in samples if s.collection_status == "collected" and s.provenance.adjudication_status == "reviewed" and not s.provenance.synthetic),
        },
    }
    trust = assess_trust(ROOT)
    payload["benchmark_trust"] = trust.as_dict()
    payload["mode"] = "release" if args.strict_quotas else "collection-progress"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n")
    if args.strict_quotas:
        print("MODE: release / --strict-quotas (quota shortfalls are errors)")
    else:
        print(
            "MODE: collection-progress (not release validation; not freeze/bakeoff/trusted-results). "
            "Pass --strict-quotas for release."
        )
    print(trust.banner())
    for msg in report.info:
        print("INFO:", msg)
    for msg in report.warnings:
        print("WARN:", msg)
    for msg in report.errors:
        print("ERROR:", msg)
    if report.errors:
        print(f"FAIL: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(f"OK: {len(report.warnings)} warning(s); collected {payload['collected_samples']} / 420")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
