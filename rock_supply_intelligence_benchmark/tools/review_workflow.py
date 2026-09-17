#!/usr/bin/env python3
"""Fail-closed human-review batching, application, and summary reconciliation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports" / "review-ledger.jsonl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def samples(include_rejected: bool = False) -> list[tuple[Path, dict[str, Any]]]:
    roots = [ROOT / "atomic", ROOT / "holdout_sealed" / "atomic"]
    if include_rejected:
        roots.append(ROOT / "rejected" / "atomic")
    result = []
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("sample_id"):
                result.append((path, data))
    return result


def reconcile(*, write: bool) -> dict[str, Any]:
    active = [(p, d) for p, d in samples() if d.get("collection_status") == "collected"]
    reviewed = [d for _, d in active if (d.get("provenance") or {}).get("adjudication_status") == "reviewed"]
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if write:
        manifest.setdefault("completeness", {})["expected_atomic_labels_reviewed"] = len(reviewed)
        review = manifest.setdefault("label_review", {})
        review["reviewed_count"] = len(reviewed)
        # Completion remains a human release action; this tool never promotes it.
        if len(reviewed) < 420:
            review["state"] = "in_progress" if reviewed else "not_complete"
            review["completed_at"] = None
            review["reviewer"] = None
        tmp = manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(tmp, manifest_path)
    return {"collected": len(active), "reviewed": len(reviewed), "written": write}


def generate(output: Path, limit: int, state: str) -> None:
    rows = []
    for path, data in samples():
        provenance = data.get("provenance") or {}
        if state != "all" and provenance.get("adjudication_status", "provisional") != state:
            continue
        rows.append((path, data))
    rows = rows[:limit] if limit else rows
    lines = ["# Human Review Batch", "", "Decide: Keep, Relabel, Reject, or Escalate.", "", "| ID | Split | Class | Source | Raw |", "| --- | --- | --- | --- | --- |"]
    for _, d in rows:
        src = d.get("source") or {}; label = d.get("labels") or {}
        lines.append(f"| `{d['sample_id']}` | {d.get('split')} | {label.get('primary_class')} | {src.get('source_locator')} | `{src.get('raw_ref')}` |")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")


def apply(decisions_path: Path, dry_run: bool) -> dict[str, Any]:
    from rock_supply_intelligence.eval.trust import assert_benchmark_unlocked
    assert_benchmark_unlocked(ROOT)
    decisions = json.loads(decisions_path.read_text())
    if not isinstance(decisions, list):
        raise ValueError("decisions file must be a JSON array")
    lookup = {
        d["sample_id"]: (p, d)
        for p, d in samples()
        if "holdout_sealed" not in p.parts
    }
    prepared: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("decision must be an object")
        required = {"decision_id", "sample_id", "decision", "reviewer", "reviewed_at", "manifest_hash", "rationale"}
        if required - decision.keys() or decision.get("decision") not in {"keep", "relabel", "reject", "escalate"}:
            raise ValueError(f"malformed decision: {decision}")
        if decision["sample_id"] not in lookup:
            raise ValueError(f"unknown or sealed sample ID: {decision['sample_id']}")
        path, data = lookup[decision["sample_id"]]
        if sha(path) != decision["manifest_hash"]:
            raise ValueError(f"stale manifest hash: {decision['sample_id']}")
        if decision["decision"] == "relabel" and not isinstance(decision.get("labels"), dict):
            raise ValueError(f"relabel requires labels: {decision['sample_id']}")
        prepared.append((path, data, decision))
    if dry_run:
        return {"dry_run": True, "decisions": len(prepared)}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    for path, data, decision in prepared:
        prov = data.setdefault("provenance", {})
        if decision["decision"] == "relabel":
            data.setdefault("labels", {}).update(decision["labels"])
        if decision["decision"] == "escalate":
            prov["adjudication_status"] = "escalated"
        else:
            prov["adjudication_status"] = "reviewed"
        prov["notes"] = (prov.get("notes", "") + f" Human review {decision['decision_id']}: {decision['decision']}.").strip()
        if decision["decision"] == "reject":
            relative = path.relative_to(ROOT / "atomic")
            target = ROOT / "rejected" / "atomic" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            path.unlink()
        else:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            os.replace(tmp, path)
        with LEDGER.open("a") as ledger:
            ledger.write(json.dumps(decision, sort_keys=True) + "\n")
    # Rejections move manifests out of the active corpus. Refresh the manifest
    # inventory before review reconciliation so the collection count cannot
    # claim fixtures that are now audit-only.
    if any(decision["decision"] == "reject" for _, _, decision in prepared):
        from materialize_atomic import update_counts
        update_counts()
    reconcile(write=True)
    return {"dry_run": False, "decisions": len(prepared)}


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reconcile").add_argument("--write", action="store_true")
    p_gen = sub.add_parser("generate"); p_gen.add_argument("--output", type=Path, required=True); p_gen.add_argument("--limit", type=int, default=20); p_gen.add_argument("--state", default="provisional", choices=["all", "provisional", "reviewed", "escalated"])
    p_apply = sub.add_parser("apply"); p_apply.add_argument("decisions", type=Path); p_apply.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "reconcile": result = reconcile(write=args.write)
    elif args.command == "generate": generate(args.output, args.limit, args.state); result = {"output": str(args.output)}
    else: result = apply(args.decisions, dry_run=not args.apply)
    print(json.dumps(result, indent=2)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
