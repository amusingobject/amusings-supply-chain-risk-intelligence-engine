#!/usr/bin/env python3
"""Compare completed generated bakeoff reports; never select a winning model."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ("schema_valid_first_pass", "schema_valid_after_retry", "materially_relevant_recall", "materially_relevant_precision", "zh_tw_relevant_recall", "unauthorized_operational_actions", "invented_business_facts", "unsupported_critical_claims")

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("reports", nargs="+", type=Path); parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(); rows = []
    for path in args.reports:
        data = json.loads(path.read_text())
        if not str(path.resolve()).startswith(str((ROOT / "runs").resolve())):
            raise SystemExit(f"report must be under benchmark runs/: {path}")
        metrics = data.get("metrics") or {}
        rows.append({"report": path.name, "provider": data.get("provider"), "model": data.get("model"), "result_class": data.get("result_class"), "n": metrics.get("n"), "elapsed_s": data.get("elapsed_s"), **{m: metrics.get(m) for m in METRICS}})
    result = {"comparison": rows, "note": "Descriptive comparison only; no model winner is selected."}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        out = args.output.resolve(); allowed = (ROOT / "runs").resolve()
        if not str(out).startswith(str(allowed)): raise SystemExit("comparison output must be under benchmark runs/")
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text)
    print(text, end=""); return 0
if __name__ == "__main__": raise SystemExit(main())
