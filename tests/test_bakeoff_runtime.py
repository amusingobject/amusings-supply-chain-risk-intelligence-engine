from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from rock_supply_intelligence.eval.harness import (
    COMPLETION_MAX_TOKENS,
    PROMPT_SOURCE_MAX_CHARS,
    evaluate_sample,
)
from rock_supply_intelligence.providers.base import CompletionRequest, CompletionResult
from rock_supply_intelligence.providers.ollama import OllamaProvider, _response_shape, _try_parse
from rock_supply_intelligence.schemas.atomic import AtomicSample


def _sample() -> AtomicSample:
    return AtomicSample.model_validate(
        {
            "sample_id": "ATOM-RUNTIME-001",
            "schema_version": "0.1",
            "split": "dev",
            "collection_status": "collected",
            "source": {
                "source_name": "runtime-test",
                "source_type": "analyst",
                "source_locator": "synthetic://runtime-test",
                "language": "en",
                "retrieved_at": "2026-01-01T00:00:00Z",
                "raw_ref": "raw/runtime.txt",
                "content_hash": "a" * 64,
            },
            "labels": {"primary_class": "irrelevant", "event_category": "irrelevant_general_world", "expected_disposition": "suppress"},
            "provenance": {"collection_plan_id": "test", "content_status": "lawful_capture", "synthetic": True},
        }
    )


class _SequencedProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.requests: list[CompletionRequest] = []

    def complete(self, request: CompletionRequest) -> CompletionResult:
        self.requests.append(request)
        if len(self.requests) == 1:
            return CompletionResult(
                text="not json",
                parsed=None,
                schema_valid=False,
                schema_errors=["json_decode: invalid"],
                diagnostics={"response_mode": request.json_mode, "response_chars": 8},
            )
        payload = {"schema_version": "0.1", "sample_id": "ATOM-RUNTIME-001", "relevance_class": "irrelevant"}
        return CompletionResult(
            text=json.dumps(payload),
            parsed=payload,
            schema_valid=True,
            diagnostics={"response_mode": request.json_mode, "response_chars": 90},
        )


class RuntimeBudgetTests(unittest.TestCase):
    def test_repair_uses_generic_json_with_safe_diagnostics_and_bounded_source(self) -> None:
        provider = _SequencedProvider()
        secret_marker = "DO-NOT-PERSIST-SOURCE-CONTENT"
        row = evaluate_sample(provider, _sample(), secret_marker + ("x" * (PROMPT_SOURCE_MAX_CHARS + 20)))

        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(provider.requests[0].json_mode, "schema")
        self.assertEqual(provider.requests[1].json_mode, "json")
        self.assertEqual(provider.requests[0].max_tokens, COMPLETION_MAX_TOKENS)
        self.assertTrue(row["input_budget"]["source_truncated"])
        self.assertEqual(row["input_budget"]["source_char_limit"], PROMPT_SOURCE_MAX_CHARS)
        self.assertTrue(row["schema_valid_after_retry"])
        self.assertEqual(row["attempt_diagnostics"][0]["schema_error_codes"], ["invalid_json_or_schema"])
        self.assertNotIn(secret_marker, json.dumps(row))

    def test_ollama_json_fallback_uses_generic_json_format(self) -> None:
        provider = OllamaProvider("model", base_url="http://example.invalid")
        request = CompletionRequest(prompt="p", system_prompt="s", json_schema={"type": "object"}, json_mode="json")
        with patch("rock_supply_intelligence.providers.ollama._post_json", return_value={"message": {"content": "{}"}}) as call:
            provider.complete(request)
        payload = call.call_args.args[1]
        self.assertEqual(payload["format"], "json")

    def test_ollama_accepts_one_json_object_inside_a_markdown_wrapper(self) -> None:
        parsed, errors = _try_parse("Here is the result:\n```json\n{\"answer\": 1}\n```")
        self.assertEqual(parsed, {"answer": 1})
        self.assertEqual(errors, [])

    def test_response_shape_does_not_retain_model_text(self) -> None:
        self.assertEqual(_response_shape("<think>hidden</think>{}"), "thinking_wrapper")
        self.assertEqual(_response_shape("Explanation: {\"a\": 1}"), "text_with_embedded_json")
        self.assertEqual(_response_shape("plain answer"), "text_without_json")

    def test_ollama_http_error_is_safe_and_actionable(self) -> None:
        provider = OllamaProvider("model", base_url="http://example.invalid")
        request = CompletionRequest(prompt="p", system_prompt="s", json_schema={"type": "object"})
        error = HTTPError("http://example.invalid/api/chat", 400, "bad", {}, None)
        with patch("rock_supply_intelligence.providers.ollama._post_json", side_effect=error):
            result = provider.complete(request)
        self.assertEqual(result.schema_errors, ["provider_http_error:400"])
        self.assertEqual(result.diagnostics["status_code"], 400)
        self.assertNotIn("http://example.invalid", json.dumps(result.diagnostics))


if __name__ == "__main__":
    unittest.main()
