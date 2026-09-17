"""Holdout isolation. Default workflows may not read holdout gold or raw."""

from __future__ import annotations

import os
from pathlib import Path

HOLDOUT_ENV = "RSI_HOLDOUT_EVAL"
SEALED_DIRNAME = "holdout_sealed"
OPEN_SPLITS = ("dev", "selection")


class HoldoutAccessError(PermissionError):
    pass


def holdout_authorized(explicit: bool = False) -> bool:
    return explicit and os.environ.get(HOLDOUT_ENV) == "1"


def require_holdout(explicit: bool) -> None:
    if not holdout_authorized(explicit):
        raise HoldoutAccessError(
            "Holdout evaluation is sealed. Pass --allow-holdout and set "
            f"{HOLDOUT_ENV}=1 in an authorized evaluation environment."
        )


def sealed_root(benchmark_root: Path) -> Path:
    return benchmark_root / SEALED_DIRNAME


def allowed_splits(allow_holdout: bool = False) -> tuple[str, ...]:
    if holdout_authorized(allow_holdout):
        return ("dev", "selection", "holdout")
    return OPEN_SPLITS


def assert_not_holdout_path(path: Path, benchmark_root: Path, allow_holdout: bool = False) -> None:
    if holdout_authorized(allow_holdout):
        return
    posix = path.resolve().as_posix()
    if SEALED_DIRNAME in posix.split("/") or "/holdout/" in posix or posix.endswith("/holdout"):
        raise HoldoutAccessError(f"refusing to read holdout path without authorization: {path}")


def path_is_holdout(path: Path, benchmark_root: Path) -> bool:
    posix = path.resolve().as_posix()
    root = benchmark_root.resolve().as_posix()
    if SEALED_DIRNAME in posix.split("/") or "/holdout/" in posix or posix.endswith("/holdout"):
        return True
    try:
        rel = path.resolve().relative_to(Path(root)).as_posix()
    except ValueError:
        return SEALED_DIRNAME in posix.split("/")
    return rel.startswith(f"{SEALED_DIRNAME}/") or "/holdout/" in f"/{rel}/"


def sample_requires_holdout(sample: object, benchmark_root: Path) -> bool:
    """True if reading this sample's raw body would access sealed/holdout content."""
    split = getattr(sample, "split", None)
    if split == "holdout":
        return True
    source = getattr(sample, "source", None)
    raw_ref = getattr(source, "raw_ref", None) or ""
    if SEALED_DIRNAME in raw_ref.split("/") or "/holdout/" in f"/{raw_ref}/":
        return True
    open_path = Path(benchmark_root) / raw_ref
    sealed_path = Path(benchmark_root) / SEALED_DIRNAME / raw_ref
    if path_is_holdout(open_path, benchmark_root):
        return True
    if not open_path.is_file() and sealed_path.is_file():
        return True
    return False


def assert_sample_permitted(sample: object, benchmark_root: Path, allow_holdout: bool = False) -> None:
    """Reject holdout samples unless explicit permission and RSI_HOLDOUT_EVAL=1."""
    if sample_requires_holdout(sample, benchmark_root):
        require_holdout(allow_holdout)
