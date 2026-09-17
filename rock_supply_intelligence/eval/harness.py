"""Atomic local-model bakeoff harness.

Runs identical prompts across providers, enforces canonical output schema,
allows one constrained schema-repair retry, and writes machine-readable reports.
Does not select a winning model.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rock_supply_intelligence.eval.access import (
    SEALED_DIRNAME,
    allowed_splits,
    assert_not_holdout_path,
    assert_sample_permitted,
    require_holdout,
)
from rock_supply_intelligence.eval.artifacts import write_generated_text
from rock_supply_intelligence.eval.trust import (
    BakeoffNotReadyError,
    assess_trust,
    require_official_bakeoff,
)
from rock_supply_intelligence.eval.gates import evaluate_gates, render_gate_report
from rock_supply_intelligence.eval.hardware import capture_hardware
from rock_supply_intelligence.eval.metrics import aggregate, score_atomic_output
from rock_supply_intelligence.eval.prompts import (
    PROMPT_VERSION,
    SCHEMA_REPAIR_PROMPT,
    SYSTEM_PROMPT,
    render_user_prompt,
)
from rock_supply_intelligence.providers.base import CompletionRequest, InferenceProvider
from rock_supply_intelligence.schemas.atomic import AtomicSample
from rock_supply_intelligence.schemas.extraction import (
    ATOMIC_EXTRACTION_JSON_SCHEMA,
    AtomicExtractionOutput,
)

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "rock_supply_intelligence_benchmark"

# This safely fits the common 4K-token Ollama context even for CJK text,
# leaving room for the system prompt, output schema, and a 512-token answer.
PROMPT_SOURCE_MAX_CHARS = 3000
COMPLETION_MAX_TOKENS = 512


def load_collected_samples(
    benchmark_root: Path | None = None,
    allow_holdout: bool = False,
) -> list[AtomicSample]:
    root = benchmark_root or BENCHMARK
    if allow_holdout:
        require_holdout(True)
    samples: list[AtomicSample] = []
    for split in allowed_splits(allow_holdout):
        for path in sorted((root / "atomic" / split).glob("*.json")):
            assert_not_holdout_path(path, root, allow_holdout=allow_holdout)
            data = json.loads(path.read_text())
            sample = AtomicSample.model_validate(data)
            if sample.collection_status == "collected":
                samples.append(sample)
        sealed = root / "holdout_sealed" / "atomic" / split
        if allow_holdout and sealed.exists():
            for path in sorted(sealed.glob("*.json")):
                data = json.loads(path.read_text())
                sample = AtomicSample.model_validate(data)
                if sample.collection_status == "collected":
                    samples.append(sample)
    return samples


def read_source_text(
    benchmark_root: Path,
    sample: AtomicSample,
    *,
    allow_holdout: bool = False,
) -> str:
    """Read raw source bytes. Sealed/holdout paths require explicit authorization."""
    assert_sample_permitted(sample, benchmark_root, allow_holdout=allow_holdout)
    open_path = benchmark_root / sample.source.raw_ref
    sealed_path = benchmark_root / SEALED_DIRNAME / sample.source.raw_ref
    path = open_path
    if not path.is_file() and sealed_path.is_file():
        require_holdout(allow_holdout)
        path = sealed_path
    assert_not_holdout_path(path, benchmark_root, allow_holdout=allow_holdout)
    if not path.is_file():
        return ""
    suffix = path.suffix.lower()
    if suffix in {".json", ".html", ".htm", ".txt", ".xml", ".csv", ".md"}:
        return path.read_text(errors="replace")
    if suffix == ".pdf":
        return _pdftotext(path)
    return path.read_bytes()[:8000].decode("utf-8", errors="replace")


def _pdftotext(path: Path) -> str:
    import shutil
    import subprocess

    binary = shutil.which("pdftotext")
    if not binary:
        return f"[PDF_UNEXTRACTED:{path.name}]"
    proc = subprocess.run(
        [binary, "-layout", str(path), "-"],
        check=False,
        capture_output=True,
        timeout=60,
    )
    return proc.stdout.decode("utf-8", errors="replace")


def evaluate_sample(
    provider: InferenceProvider,
    sample: AtomicSample,
    source_text: str,
) -> dict[str, Any]:
    source_truncated = len(source_text) > PROMPT_SOURCE_MAX_CHARS
    user = render_user_prompt(
        sample.sample_id,
        sample.source.model_dump(),
        source_text,
        max_chars=PROMPT_SOURCE_MAX_CHARS,
    )
    input_budget = {
        "source_chars_original": len(source_text),
        "source_chars_sent": min(len(source_text), PROMPT_SOURCE_MAX_CHARS),
        "source_truncated": source_truncated,
        "source_char_limit": PROMPT_SOURCE_MAX_CHARS,
        "completion_token_limit": COMPLETION_MAX_TOKENS,
    }
    request = CompletionRequest(
        prompt=user,
        json_schema=ATOMIC_EXTRACTION_JSON_SCHEMA,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.0,
        seed=0,
        max_tokens=COMPLETION_MAX_TOKENS,
        json_mode="schema",
    )
    first = provider.complete(request)
    first_valid = False
    parsed = first.parsed
    if parsed is not None:
        try:
            AtomicExtractionOutput.model_validate(parsed)
            first_valid = True
        except ValidationError:
            first.schema_errors.append("output_validation_error")
            first_valid = False
    first_attempt = _attempt_diagnostics(first, canonical_schema_valid=first_valid)
    retry_used = False
    after_retry = first_valid
    if not first_valid:
        retry_used = True
        repair = CompletionRequest(
            prompt=SCHEMA_REPAIR_PROMPT.format(
                errors="\n".join(first.schema_errors) or "invalid JSON",
                sample_id=sample.sample_id,
            )
            + "\n\nOriginal user task:\n"
            + user,
            json_schema=ATOMIC_EXTRACTION_JSON_SCHEMA,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0,
            seed=0,
            max_tokens=COMPLETION_MAX_TOKENS,
            # Some Ollama backends reject full JSON Schema.  Generic JSON is
            # still deterministic and the canonical Pydantic check stays
            # fail-closed after the response returns.
            json_mode="json",
        )
        second = provider.complete(repair)
        second_valid = False
        parsed = second.parsed
        if parsed is not None:
            try:
                AtomicExtractionOutput.model_validate(parsed)
                second_valid = True
            except ValidationError:
                second.schema_errors.append("output_validation_error")
        after_retry = second_valid
        second_attempt = _attempt_diagnostics(second, canonical_schema_valid=second_valid)
        first.latency_ms += second.latency_ms
        first.retry_used = True
        first.parsed = parsed
        first.schema_valid = after_retry
    row = score_atomic_output(sample, parsed, first_valid, after_retry, source_text=source_text)
    row.update(
        {
            "provider": first.provider or provider.name,
            "model": provider.model,
            "latency_ms": first.latency_ms,
            "retry_used": retry_used,
            "prompt_version": PROMPT_VERSION,
            "input_budget": input_budget,
            "attempt_diagnostics": [
                first_attempt,
                *([second_attempt] if retry_used else []),
            ],
        }
    )
    return row


def _attempt_diagnostics(result: Any, *, canonical_schema_valid: bool) -> dict[str, Any]:
    """Persist only source-free diagnostics; never write prompt/model text."""
    details = dict(getattr(result, "diagnostics", {}) or {})
    details.update(
        {
            "schema_valid": canonical_schema_valid,
            "schema_error_codes": [_safe_error_code(error) for error in result.schema_errors],
            "latency_ms": result.latency_ms,
        }
    )
    return details


def _safe_error_code(error: str) -> str:
    if error.startswith("provider_http_error:"):
        return error
    if error.startswith("provider_error:"):
        return error
    if error == "output_validation_error":
        return error
    return "invalid_json_or_schema"


def run_bakeoff(
    provider: InferenceProvider,
    samples: list[AtomicSample] | None = None,
    benchmark_root: Path | None = None,
    report_dir: Path | None = None,
    allow_holdout: bool = False,
    *,
    development_only: bool = False,
) -> dict[str, Any]:
    root = benchmark_root or BENCHMARK
    if development_only and allow_holdout:
        raise BakeoffNotReadyError(
            "development-only bakeoff cannot include holdout data. "
            "Official comparable bakeoff requires a TRUSTED locked benchmark."
        )
    allow_holdout = False if development_only else allow_holdout
    if allow_holdout:
        require_holdout(True)
    supplied = samples is not None
    if supplied:
        for sample in samples:
            assert_sample_permitted(sample, root, allow_holdout=allow_holdout)
    if development_only:
        assessed = assess_trust(root)
        if not supplied:
            samples = load_collected_samples(root, allow_holdout=False)
    else:
        assessed = require_official_bakeoff(root)
        if not supplied:
            samples = load_collected_samples(root, allow_holdout=allow_holdout)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for sample in samples:
        text = read_source_text(root, sample, allow_holdout=allow_holdout)
        rows.append(evaluate_sample(provider, sample, text))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "provider": provider.name,
        "model": provider.model,
        "hardware": capture_hardware(),
        "metrics": aggregate(rows),
        "samples": rows,
        "elapsed_s": time.perf_counter() - started,
        "allow_holdout": allow_holdout,
        "development_only": development_only,
        "benchmark_trust": assessed.as_dict(),
        "result_class": "official" if assessed.release_ready and not development_only else "development_untrusted",
        "claims_benchmark_validity": bool(assessed.release_ready and not development_only),
    }
    report["gates"] = evaluate_gates(report["metrics"])
    out_dir = report_dir or (root / "runs")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "dev-untrusted-" if development_only or not assessed.release_ready else ""
    json_path = Path(out_dir) / f"{prefix}atomic-bakeoff-{provider.name}-{stamp}.json"
    md_path = Path(out_dir) / f"{prefix}atomic-bakeoff-{provider.name}-{stamp}.md"
    write_generated_text(json_path, json.dumps(report, indent=2) + "\n", root)
    write_generated_text(md_path, _render_markdown(report), root)
    report["json_path"] = str(json_path)
    report["md_path"] = str(md_path)
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    trust = report.get("benchmark_trust") or {}
    lines = [
        f"# Atomic bakeoff report",
        "",
        f"**Benchmark trust: {trust.get('status', 'UNKNOWN')} / release_ready={trust.get('release_ready')}**",
        f"**Result class: {report.get('result_class')} — claims_benchmark_validity={report.get('claims_benchmark_validity')}**",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- provider: {report['provider']}",
        f"- model: {report['model']}",
        f"- prompt_version: {report['prompt_version']}",
        f"- n: {m['n']}",
        f"- schema_valid_first_pass: {m['schema_valid_first_pass']}",
        f"- schema_valid_after_retry: {m['schema_valid_after_retry']}",
        f"- materially_relevant_recall: {m['materially_relevant_recall']}",
        f"- materially_relevant_precision: {m['materially_relevant_precision']}",
        f"- zh_tw_relevant_recall: {m['zh_tw_relevant_recall']}",
        f"- unauthorized_operational_actions: {m['unauthorized_operational_actions']}",
        f"- invented_business_facts: {m['invented_business_facts']}",
        f"- unsupported_critical_claims: {m['unsupported_critical_claims']}",
        "",
        "This report does not declare a winning model.",
        "",
    ]
    if report.get("development_only") or not trust.get("release_ready"):
        lines.append(
            "DRAFT/UNTRUSTED: this run is not an official comparable bakeoff. "
            "It must not be cited as frozen benchmark validity."
        )
        lines.append("")
        for item in trust.get("unmet") or []:
            lines.append(f"- unmet: {item}")
        lines.append("")
    lines.append(render_gate_report(report.get("gates") or evaluate_gates(m)))
    return "\n".join(lines)
