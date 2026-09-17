#!/usr/bin/env python3
"""Move holdout gold labels and holdout-only raw files into holdout_sealed/."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEALED = ROOT / "holdout_sealed"


def _move(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.move(str(src), str(dest))


def main() -> int:
    import sys

    project = ROOT.parent
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from rock_supply_intelligence.eval.trust import assert_benchmark_unlocked

    assert_benchmark_unlocked(ROOT)
    SEALED.mkdir(parents=True, exist_ok=True)
    (SEALED / "ACCESS.json").write_text(
        json.dumps(
            {
                "status": "sealed",
                "rule": "Default development and model-selection workflows must not read this tree.",
                "authorization": "RSI_HOLDOUT_EVAL=1 and --allow-holdout",
            },
            indent=2,
        )
        + "\n"
    )
    holdout_ids = set()
    for path in list((ROOT / "atomic" / "holdout").glob("*.json")):
        data = json.loads(path.read_text())
        holdout_ids.add(data["sample_id"])
        raw = ROOT / data["source"]["raw_ref"]
        if raw.is_file():
            _move(raw, SEALED / data["source"]["raw_ref"])
            data["source"]["raw_ref"] = data["source"]["raw_ref"]
        _move(path, SEALED / "atomic" / "holdout" / path.name)
    for path in list((ROOT / "scenarios" / "holdout").glob("*.json")):
        _move(path, SEALED / "scenarios" / "holdout" / path.name)
    batch = ROOT / "atomic" / "first20_fixtures.json"
    if batch.exists():
        doc = json.loads(batch.read_text())
        if isinstance(doc, dict) and "fixtures" in doc:
            doc["fixtures"] = [f for f in doc["fixtures"] if f.get("split") != "holdout"]
            doc["notes"] = (doc.get("notes") or "") + " Holdout fixtures removed from the open batch index."
            batch.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    (ROOT / "atomic" / "holdout").mkdir(exist_ok=True)
    (ROOT / "scenarios" / "holdout").mkdir(exist_ok=True)
    index_path = ROOT / "scenarios" / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text())
        for item in index.get("scenarios") or []:
            if item.get("split") == "holdout" and item.get("path"):
                name = Path(item["path"]).name
                sealed_path = f"holdout_sealed/scenarios/holdout/{name}"
                if (ROOT / sealed_path).exists():
                    item["path"] = sealed_path
        index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"sealed {len(holdout_ids)} atomic holdout samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
