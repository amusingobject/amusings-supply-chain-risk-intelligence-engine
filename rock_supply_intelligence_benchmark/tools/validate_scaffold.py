#!/usr/bin/env python3
"""Dependency-free structural validation for the benchmark scaffold."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["README.md", "VERSION", "manifest.json", "schemas", "atomic/dev", "atomic/selection", "atomic/holdout", "scenarios/dev", "scenarios/selection", "scenarios/holdout", "raw", "expected", "scoring", "reports"]
for name in REQUIRED:
    assert (ROOT / name).exists(), f"missing required path: {name}"
for file in ROOT.rglob("*.json"):
    try:
        json.loads(file.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {file.relative_to(ROOT)}: {exc}") from exc
for schema in ["benchmark-manifest.schema.json", "atomic-osint-sample.schema.json", "scenario-manifest.schema.json"]:
    assert (ROOT / "schemas" / schema).is_file(), f"missing required schema: {schema}"
index = json.loads((ROOT / "scenarios/index.json").read_text())
actual = []
for split in ("dev", "selection", "holdout"):
    for path in (ROOT / "scenarios" / split).glob("*.json"):
        item = json.loads(path.read_text()); actual.append(item)
sealed = ROOT / "holdout_sealed" / "scenarios" / "holdout"
if sealed.exists():
    for path in sealed.glob("*.json"):
        actual.append(json.loads(path.read_text()))
assert len(actual) == 28, f"expected 28 official scenario manifests, got {len(actual)}"
assert len({x["scenario_id"] for x in actual}) == 28, "duplicate scenario ID"
assert Counter(x["split"] for x in actual) == {"dev": 8, "selection": 10, "holdout": 10}, "wrong scenario split"
assert len(index["scenarios"]) == 28, "index mismatch"
corpus = json.loads((ROOT / "atomic/corpus_manifest.json").read_text())
assert corpus["target_samples"] == 420 and corpus["split_targets"] == {"dev":120,"selection":150,"holdout":150}
print("OK: 28 scenario manifests; atomic collection remains %d / %d." % (corpus["collected_samples"], corpus["target_samples"]))
