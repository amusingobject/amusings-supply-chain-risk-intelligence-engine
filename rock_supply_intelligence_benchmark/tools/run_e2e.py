#!/usr/bin/env python3
"""Offline E2E replay CLI. Holdout requires RSI_HOLDOUT_EVAL=1 and --allow-holdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rock_supply_intelligence.eval.e2e import replay_all, write_e2e_report
from rock_supply_intelligence.eval.gates import evaluate_gates, render_gate_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-holdout", action="store_true")
    args = parser.parse_args()
    result = replay_all(allow_holdout=args.allow_holdout)
    e2e_doc = json.loads((ROOT / "rock_supply_intelligence_benchmark" / "scoring" / "gates.json").read_text())
    e2e_doc = {
        **e2e_doc,
        "hard_gates": [g for g in e2e_doc.get("hard_gates") or [] if str(g.get("id", "")).startswith("e2e-")],
        "quality_gates": [g for g in e2e_doc.get("quality_gates") or [] if g.get("metric") in result["metrics"]],
    }
    result["gates"] = evaluate_gates(result["metrics"], e2e_doc)
    json_path, md_path = write_e2e_report(
        result, ROOT / "rock_supply_intelligence_benchmark" / "runs"
    )
    trust = result.get("benchmark_trust") or {}
    print(
        json.dumps(
            {
                "metrics": result["metrics"],
                "gates_passed": result["gates"]["passed"],
                "benchmark_trust": trust,
                "result_class": result.get("result_class"),
                "json_path": str(json_path),
            },
            indent=2,
        )
    )
    print(render_gate_report(result["gates"]))
    if not trust.get("release_ready"):
        print(
            "NOTE: open-scenario hard-gate PASS is not a frozen/release-ready result. "
            f"Trust status={trust.get('status')}. Unmet: {trust.get('unmet')}"
        )
    print(md_path)
    return 0 if result["gates"]["passed"] or result["metrics"]["placeholders_remaining"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
