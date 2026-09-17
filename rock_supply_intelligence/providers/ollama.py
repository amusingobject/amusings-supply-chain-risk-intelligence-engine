"""Ollama local provider (HTTP). Secrets are never sent in prompts."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rock_supply_intelligence.providers.base import CompletionRequest, CompletionResult


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        model_hash: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.model_hash = model_hash

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if request.json_mode not in {"schema", "json"}:
            raise ValueError(f"unsupported json_mode: {request.json_mode}")
        payload = {
            "model": self.model,
            "stream": False,
            "format": request.json_schema if request.json_mode == "schema" else "json",
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.seed is not None:
            payload["options"]["seed"] = request.seed
        started = time.perf_counter()
        try:
            raw = _post_json(f"{self.base_url}/api/chat", payload, request.timeout_s)
        except HTTPError as exc:
            return CompletionResult(
                text="",
                parsed=None,
                schema_valid=False,
                schema_errors=[f"provider_http_error:{exc.code}"],
                latency_ms=(time.perf_counter() - started) * 1000,
                provider=self.name,
                model=self.model,
                model_hash=self.model_hash,
                diagnostics={
                    "response_mode": request.json_mode,
                    "error_kind": "http",
                    "status_code": exc.code,
                },
            )
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return CompletionResult(
                text="",
                parsed=None,
                schema_valid=False,
                schema_errors=[f"provider_error:{type(exc).__name__}"],
                latency_ms=(time.perf_counter() - started) * 1000,
                provider=self.name,
                model=self.model,
                model_hash=self.model_hash,
                diagnostics={"response_mode": request.json_mode, "error_kind": type(exc).__name__},
            )
        latency_ms = (time.perf_counter() - started) * 1000
        text = ((raw.get("message") or {}).get("content")) or ""
        parsed, errors = _try_parse(text)
        return CompletionResult(
            text=text,
            parsed=parsed,
            schema_valid=not errors and parsed is not None,
            schema_errors=errors,
            latency_ms=latency_ms,
            provider=self.name,
            model=self.model,
            model_hash=self.model_hash,
            raw={"eval_count": raw.get("eval_count"), "eval_duration": raw.get("eval_duration")},
            diagnostics={
                "response_mode": request.json_mode,
                "response_chars": len(text),
                "response_shape": _response_shape(text),
                "parse_error_kinds": [_error_kind(error) for error in errors],
            },
        )


def _post_json(url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _try_parse(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        _, _, cleaned = cleaned.partition("\n")
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Some otherwise-capable local models prepend a short explanation or
        # wrap their JSON in a Markdown fence.  Recover exactly one complete
        # JSON object, then leave canonical schema and safety validation
        # fail-closed.  We never persist this text in diagnostics.
        start = cleaned.find("{")
        if start >= 0:
            try:
                value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
            except json.JSONDecodeError:
                return None, [f"json_decode: {exc}"]
        else:
            return None, [f"json_decode: {exc}"]
    if not isinstance(value, dict):
        return None, ["json_not_object"]
    return value, []


def _error_kind(error: str) -> str:
    """Keep persisted diagnostics useful without persisting model/source text."""
    return error.split(":", 1)[0]


def _response_shape(text: str) -> str:
    """Classify output form without retaining any model or source text."""
    stripped = text.strip()
    if not stripped:
        return "empty"
    if stripped.startswith("```"):
        return "markdown_fence"
    if stripped.startswith("<think>"):
        return "thinking_wrapper"
    if stripped.startswith("{"):
        return "json_object_or_malformed_json"
    if "{" in stripped:
        return "text_with_embedded_json"
    return "text_without_json"
