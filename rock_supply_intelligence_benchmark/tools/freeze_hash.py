#!/usr/bin/env python3
"""Create or verify the deterministic SHA-256 content tree for benchmark lock."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from rock_supply_intelligence.eval.trust import (
    FrozenBenchmarkError,
    assert_benchmark_unlocked,
    assess_trust,
    freeze_allowed,
    freeze_root_hash,
    freeze_tree_entries,
)

EXCLUDED_DIRS = {"reports", "runs", "__pycache__", ".git"}
EXCLUDED_FILES = {"manifest.json", "tools/freeze_hash.py"}


def tree(root: Path | None = None) -> dict[str, str]:
    return freeze_tree_entries(root or ROOT)


def root_hash(entries: dict[str, str]) -> str:
    return freeze_root_hash(entries)


def _write_manifest(manifest: dict) -> None:
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["show", "verify", "freeze", "lock"])
    args = parser.parse_args()
    entries = tree()
    current = root_hash(entries)
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    frozen = (manifest.get("freeze") or {}).get("tree_hash")
    if args.command == "show":
        print(json.dumps({"tree_hash": current, "files": entries}, indent=2))
        return 0
    if args.command == "verify":
        if not frozen:
            print("UNLOCKED: no freeze hash recorded; current candidate=" + current)
            return 2
        if frozen != current:
            print("MISMATCH: recorded=" + frozen + " current=" + current)
            return 1
        print("OK: " + current)
        return 0
    try:
        assert_benchmark_unlocked(ROOT)
    except FrozenBenchmarkError as exc:
        print(str(exc))
        return 1
    trust = assess_trust(ROOT)
    blocking = freeze_allowed(trust)
    if args.command == "freeze":
        if blocking:
            print("Freeze refused until corpus, quotas, and label review are complete.")
            for item in blocking:
                print("- " + item)
            return 1
        manifest.setdefault("freeze", {})
        manifest["freeze"]["tree_hash"] = current
        _write_manifest(manifest)
        print(
            "Recorded freeze hash "
            + current
            + ". Benchmark remains unlocked until `freeze_hash.py lock` with a valid RFC 3339 locked_at."
        )
        return 0
    # lock
    if blocking:
        print("Lock refused until corpus, quotas, and label review are complete.")
        for item in blocking:
            print("- " + item)
        return 1
    if not frozen:
        print("Lock refused: record a freeze hash first via `freeze_hash.py freeze`.")
        return 1
    if frozen != current:
        print("Lock refused: recorded tree_hash does not match current tree.")
        return 1
    manifest["status"] = "locked"
    manifest.setdefault("freeze", {})
    manifest["freeze"]["tree_hash"] = current
    manifest["freeze"]["locked_at"] = _now()
    _write_manifest(manifest)
    print("LOCKED at " + manifest["freeze"]["locked_at"] + " hash=" + current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
