"""Hard-gate executor. Thresholds are not relaxed to pass tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GATES = ROOT / "rock_supply_intelligence_benchmark" / "scoring" / "gates.json"

OPS: dict[str, Callable[[float, float], bool]] = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
}


def load_gates(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or DEFAULT_GATES).read_text())


def _get(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    if value is None:
        return None
    return float(value)


def evaluate_gates(metrics: dict[str, Any], gates_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = gates_doc or load_gates()
    results = []
    failed = []
    for gate in doc.get("hard_gates") or []:
        metric = gate["metric"]
        op = gate["operator"]
        threshold = float(gate["threshold"])
        actual = _get(metrics, metric)
        if actual is None:
            passed = False
            detail = "metric_missing"
        else:
            passed = OPS[op](actual, threshold)
            detail = "ok" if passed else "threshold_failed"
        row = {
            "id": gate.get("id") or metric,
            "scope": gate.get("scope"),
            "metric": metric,
            "operator": op,
            "threshold": threshold,
            "actual": actual,
            "passed": passed,
            "detail": detail,
            "kind": "hard",
        }
        results.append(row)
        if not passed:
            failed.append(row)
    for gate in doc.get("quality_gates") or []:
        metric = gate["metric"]
        actual = _get(metrics, metric)
        passed = actual is not None and OPS[gate["operator"]](actual, float(gate["threshold"]))
        results.append(
            {
                "id": gate.get("id") or metric,
                "metric": metric,
                "operator": gate["operator"],
                "threshold": float(gate["threshold"]),
                "actual": actual,
                "passed": passed,
                "kind": "quality",
            }
        )
    return {
        "passed": not failed,
        "hard_gate_failures": failed,
        "results": results,
    }


def render_gate_report(evaluation: dict[str, Any]) -> str:
    lines = ["# Gate report", ""]
    lines.append(f"Overall hard gates: {'PASS' if evaluation['passed'] else 'FAIL'}")
    lines.append("")
    for row in evaluation["results"]:
        flag = "PASS" if row["passed"] else "FAIL"
        actual = row.get("actual")
        lines.append(
            f"- {flag} {row.get('id')} {row['metric']} {row['operator']} {row['threshold']} actual={actual}"
        )
    return "\n".join(lines) + "\n"
