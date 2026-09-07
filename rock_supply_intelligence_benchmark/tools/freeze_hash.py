#!/usr/bin/env python3
"""Create or verify the deterministic SHA-256 content tree for benchmark lock."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {"reports", "__pycache__", ".git"}
EXCLUDED_FILES = {"manifest.json", "tools/freeze_hash.py"}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree() -> dict[str, str]:
    result = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in EXCLUDED_FILES:
            continue
        result[relative] = digest(path)
    return result

def root_hash(entries: dict[str, str]) -> str:
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["show", "verify", "freeze"])
    args = parser.parse_args()
    entries = tree(); current = root_hash(entries)
    manifest_path = ROOT / "manifest.json"; manifest = json.loads(manifest_path.read_text())
    frozen = manifest["freeze"].get("tree_hash")
    if args.command == "show":
        print(json.dumps({"tree_hash": current, "files": entries}, indent=2)); return 0
    if args.command == "verify":
        if not frozen:
            print("UNLOCKED: no freeze hash recorded; current candidate=" + current); return 2
        if frozen != current:
            print("MISMATCH: recorded=" + frozen + " current=" + current); return 1
        print("OK: " + current); return 0
    if manifest.get("status") == "locked":
        print("Refusing to overwrite locked benchmark; create a new version."); return 1
    manifest["freeze"]["tree_hash"] = current
    manifest["freeze"]["locked_at"] = "SET_BY_RELEASE_MANAGER"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Recorded candidate freeze hash " + current + "; set locked_at and status only after human review.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
