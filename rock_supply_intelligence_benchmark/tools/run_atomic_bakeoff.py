#!/usr/bin/env python3
"""Run the atomic OSINT bakeoff against a configured provider. Does not pick a winner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rock_supply_intelligence.eval.harness import run_bakeoff
from rock_supply_intelligence.providers.ollama import OllamaProvider
from rock_supply_intelligence.providers.openai_compat import OpenAICompatProvider
from rock_supply_intelligence.eval.run_spec import BakeoffRunSpec, write_run_spec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["ollama", "openai_compat"], default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--execution-class", default="local", choices=["local", "cloud"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--sample-id",
        action="append",
        default=[],
        help="Open-fixture sample ID to evaluate; repeat for a deterministic selected set.",
    )
    parser.add_argument("--model-hash", default=None)
    parser.add_argument(
        "--allow-holdout",
        action="store_true",
        help="Authorized holdout evaluation. Also requires RSI_HOLDOUT_EVAL=1.",
    )
    parser.add_argument(
        "--development-only",
        action="store_true",
        help="Untrusted open-dev run. Does not claim benchmark validity and cannot read holdout.",
    )
    args = parser.parse_args()
    spec = BakeoffRunSpec(
        provider=args.provider, model=args.model,
        base_url=args.base_url or ("http://127.0.0.1:11434" if args.provider == "ollama" else "http://127.0.0.1:8000/v1"),
        execution_class=args.execution_class, development_only=args.development_only,
        model_hash=args.model_hash,
    )
    try:
        spec.validate()
    except ValueError as exc:
        print(f"invalid run specification: {exc}", file=sys.stderr)
        return 2
    from rock_supply_intelligence.eval.trust import BakeoffNotReadyError, require_official_bakeoff

    if not args.development_only:
        try:
            require_official_bakeoff(ROOT / "rock_supply_intelligence_benchmark")
        except BakeoffNotReadyError as exc:
            print(str(exc), file=sys.stderr)
            print(
                "Re-run with --development-only for an explicitly untrusted open-dev bakeoff.",
                file=sys.stderr,
            )
            return 2
    if args.provider == "ollama":
        provider = OllamaProvider(model=args.model, base_url=spec.base_url, model_hash=args.model_hash)
    else:
        provider = OpenAICompatProvider(
            model=args.model,
            base_url=spec.base_url,
            execution_class=args.execution_class,
            model_hash=args.model_hash,
        )
    from rock_supply_intelligence.eval.harness import load_collected_samples

    allow_holdout = args.allow_holdout and not args.development_only
    samples = load_collected_samples(allow_holdout=allow_holdout)
    if args.sample_id:
        requested = set(args.sample_id)
        selected = [sample for sample in samples if sample.sample_id in requested]
        found = {sample.sample_id for sample in selected}
        missing = sorted(requested - found)
        if missing:
            print(f"requested sample IDs are unavailable or not permitted: {', '.join(missing)}", file=sys.stderr)
            return 2
        samples = selected
    if args.limit:
        samples = samples[: args.limit]
    report = run_bakeoff(
        provider,
        samples=samples,
        allow_holdout=allow_holdout,
        development_only=args.development_only,
    )
    write_run_spec(spec, Path(report["json_path"]).parent)
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "benchmark_trust": report.get("benchmark_trust"),
                "result_class": report.get("result_class"),
                "claims_benchmark_validity": report.get("claims_benchmark_validity"),
                "json_path": report["json_path"],
                "md_path": report["md_path"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
