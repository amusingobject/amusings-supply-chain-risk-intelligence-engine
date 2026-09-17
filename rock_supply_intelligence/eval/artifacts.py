"""Generated-output path protection. Replay/bakeoff may not write ground truth."""

from __future__ import annotations

from pathlib import Path

from rock_supply_intelligence.eval.trust import FrozenBenchmarkError, freeze_tree_entries, is_locked

GENERATED_DIRNAMES = frozenset({"runs", "reports"})
PROTECTED_DIRNAMES = frozenset(
    {
        "expected",
        "holdout_sealed",
        "scenarios",
        "atomic",
        "raw",
        "scoring",
        "schemas",
    }
)
PROTECTED_FILES = frozenset(
    {
        "manifest.json",
        "VERSION",
        "FREEZE.md",
        "atomic/corpus_manifest.json",
        "scenarios/index.json",
    }
)


class ProtectedOutputError(ValueError):
    pass


def assert_generated_output_dir(report_dir: Path, benchmark_root: Path) -> Path:
    """Allow only runs/ or reports/ under the benchmark root (or an obvious temp dir)."""
    dest = report_dir.resolve()
    root = benchmark_root.resolve()
    parts = set(dest.parts)
    blocked = sorted(parts & PROTECTED_DIRNAMES)
    if blocked:
        raise ProtectedOutputError(
            "benchmark run output must not write under ground-truth directories "
            f"{blocked}: {dest}"
        )
    try:
        rel = dest.relative_to(root)
    except ValueError:
        return dest
    if not rel.parts or rel.parts[0] not in GENERATED_DIRNAMES:
        raise ProtectedOutputError(
            "benchmark run output must be written under runs/ or reports/, not "
            f"{rel.as_posix() or '.'}"
        )
    return dest


def assert_not_frozen_file(path: Path, benchmark_root: Path) -> None:
    """Refuse to overwrite a file that belongs to the freeze tree."""
    target = path.resolve()
    root = benchmark_root.resolve()
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return
    if rel in PROTECTED_FILES or any(rel == name or rel.startswith(name + "/") for name in PROTECTED_DIRNAMES):
        raise ProtectedOutputError(f"refusing to overwrite benchmark input {rel}")
    if is_locked(benchmark_root) and rel not in {"manifest.json"}:
        entries = freeze_tree_entries(benchmark_root)
        if rel in entries:
            raise FrozenBenchmarkError(
                f"refusing to overwrite frozen benchmark file {rel}; create a new benchmark version"
            )


def write_generated_text(path: Path, text: str, benchmark_root: Path) -> Path:
    dest = Path(path)
    assert_generated_output_dir(dest.parent, benchmark_root)
    assert_not_frozen_file(dest, benchmark_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest
