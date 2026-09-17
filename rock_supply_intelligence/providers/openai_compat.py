"""OpenAI-compatible HTTP provider (vLLM, llama.cpp server, optional cloud).

This adapter is used for any endpoint that speaks the chat.completions API.
The application layer never sees vendor-specific fields.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rock_supply_intelligence.providers.base import CompletionRequest, CompletionResult
from rock_supply_intelligence.providers.ollama import _try_parse


class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key_env: str = "RSI_INFERENCE_API_KEY",
        model_hash: str | None = None,
        execution_class: str = "local",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.model_hash = model_hash
        self.execution_class = execution_class

    def complete(self, request: CompletionRequest) -> CompletionResult:
        if request.json_mode not in {"schema", "json"}:
            raise ValueError(f"unsupported json_mode: {request.json_mode}")
        api_key = os.environ.get(self.api_key_env, "")
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": (
                {"type": "json_schema", "json_schema": {"name": "atomic_extraction", "schema": request.json_schema, "strict": True}}
                if request.json_mode == "schema"
                else {"type": "json_object"}
            ),
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        started = time.perf_counter()
        try:
            raw = _post_json(f"{self.base_url}/chat/completions", payload, headers, request.timeout_s)
        except HTTPError as exc:
            return CompletionResult(
                text="",
                parsed=None,
                schema_valid=False,
                schema_errors=[f"provider_http_error:{exc.code}"],
                latency_ms=(time.perf_counter() - started) * 1000,
                provider=f"{self.name}:{self.execution_class}",
                model=self.model,
                model_hash=self.model_hash,
                diagnostics={"response_mode": request.json_mode, "error_kind": "http", "status_code": exc.code},
            )
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            return CompletionResult(
                text="",
                parsed=None,
                schema_valid=False,
                schema_errors=[f"provider_error:{type(exc).__name__}"],
                latency_ms=(time.perf_counter() - started) * 1000,
                provider=f"{self.name}:{self.execution_class}",
                model=self.model,
                model_hash=self.model_hash,
                diagnostics={"response_mode": request.json_mode, "error_kind": type(exc).__name__},
            )
        latency_ms = (time.perf_counter() - started) * 1000
        text = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
        parsed, errors = _try_parse(text)
        return CompletionResult(
            text=text,
            parsed=parsed,
            schema_valid=not errors and parsed is not None,
            schema_errors=errors,
            latency_ms=latency_ms,
            provider=f"{self.name}:{self.execution_class}",
            model=self.model,
            model_hash=self.model_hash,
            raw={"usage": raw.get("usage")},
            diagnostics={
                "response_mode": request.json_mode,
                "response_chars": len(text),
                "parse_error_kinds": [error.split(":", 1)[0] for error in errors],
            },
        )


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))
