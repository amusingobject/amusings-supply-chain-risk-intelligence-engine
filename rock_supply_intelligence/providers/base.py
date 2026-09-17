"""Provider-agnostic inference interface.

The rest of the application must not care whether a result came from Ollama,
llama.cpp, vLLM, or a cloud vendor. Cloud and local providers return the same
canonical structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class CompletionRequest:
    prompt: str
    json_schema: dict[str, Any]
    system_prompt: str
    temperature: float = 0.0
    max_tokens: int = 2048
    seed: int | None = 0
    timeout_s: float = 120.0
    # "schema" requests provider-native structured output.  "json" is the
    # deterministic compatibility fallback used only for the constrained
    # repair attempt when a provider cannot honor the full schema mode.
    json_mode: str = "schema"


@dataclass
class CompletionResult:
    text: str
    parsed: dict[str, Any] | None
    schema_valid: bool
    schema_errors: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    retry_used: bool = False
    provider: str = ""
    model: str = ""
    model_hash: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    # Deliberately source-free metadata suitable for persisted bakeoff reports.
    diagnostics: dict[str, Any] = field(default_factory=dict)


class InferenceProvider(Protocol):
    name: str
    model: str

    def complete(self, request: CompletionRequest) -> CompletionResult:
        """Return a structured completion. Must not execute tools or writes."""
        ...
