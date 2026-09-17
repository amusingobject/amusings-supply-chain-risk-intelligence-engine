#!/usr/bin/env python3
"""Report bakeoff blockers without invoking a model or reading holdout data."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from rock_supply_intelligence.eval.run_spec import BakeoffRunSpec
from rock_supply_intelligence.eval.trust import assess_trust

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--provider", default="ollama"); parser.add_argument("--model", required=True); parser.add_argument("--base-url", default="http://127.0.0.1:11434"); parser.add_argument("--development-only", action="store_true")
    args = parser.parse_args()
    spec = BakeoffRunSpec(provider=args.provider, model=args.model, base_url=args.base_url, development_only=args.development_only)
    try: spec.validate(); spec_error = None
    except ValueError as exc: spec_error = str(exc)
    trust = assess_trust(ROOT / "rock_supply_intelligence_benchmark", include_tree_hash=False)
    result = {"run_spec_fingerprint": spec.fingerprint(), "run_spec_error": spec_error, "development_only": args.development_only, "official_ready": trust.release_ready, "official_blockers": trust.unmet, "holdout_read": False}
    print(json.dumps(result, indent=2)); return 0 if args.development_only and not spec_error else (0 if trust.release_ready and not spec_error else 2)
if __name__ == "__main__": raise SystemExit(main())
