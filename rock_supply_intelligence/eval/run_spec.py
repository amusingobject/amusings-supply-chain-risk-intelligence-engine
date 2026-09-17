"""Versioned, hashable configuration for reproducible development bakeoffs."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BakeoffRunSpec:
    provider: str
    model: str
    base_url: str
    execution_class: str = "local"
    temperature: float = 0.0
    seed: int = 0
    max_tokens: int = 2048
    timeout_s: float = 120.0
    prompt_version: str = "atomic-extraction-v0.1"
    splits: tuple[str, ...] = ("dev", "selection")
    development_only: bool = True
    model_hash: str | None = None

    def normalized(self) -> dict[str, Any]:
        data = asdict(self); data["splits"] = list(self.splits)
        return data

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.normalized(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def validate(self) -> None:
        if self.provider not in {"ollama", "openai_compat"}: raise ValueError("unsupported provider")
        if self.execution_class not in {"local", "cloud"}: raise ValueError("invalid execution_class")
        if self.development_only and "holdout" in self.splits: raise ValueError("development-only runs cannot select holdout")
        if self.temperature != 0.0 or self.seed is None: raise ValueError("comparable runs require temperature=0 and an explicit seed")
        if self.max_tokens < 1 or self.timeout_s <= 0: raise ValueError("invalid token limit or timeout")


def write_run_spec(spec: BakeoffRunSpec, directory: Path) -> Path:
    spec.validate(); directory.mkdir(parents=True, exist_ok=True)
    path = directory / "run-spec.json"
    payload = {"fingerprint": spec.fingerprint(), "spec": spec.normalized()}
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path
