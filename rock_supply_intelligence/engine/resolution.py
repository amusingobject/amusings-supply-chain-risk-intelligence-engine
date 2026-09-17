"""Fail-closed identity, alias, and configuration resolution.

Malformed or conflicting input never becomes a normal business decision.
There is no first-match precedence unless an explicit validated priority exists.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PROFILE_VERSION = "resolution-v0.1"

ResolutionStatus = Literal[
    "VALID",
    "AMBIGUOUS",
    "INVALID_PROFILE",
    "UNRESOLVED",
    "REVIEW_REQUIRED",
]

ERROR_CODES = (
    "INVALID_PROFILE",
    "CONFIG_ERROR",
    "AMBIGUOUS_ALIAS",
    "AMBIGUOUS_HEADER",
    "DUPLICATE_IDENTITY",
    "UNRESOLVED_IDENTITY",
    "BLANK_IDENTITY",
    "MALFORMED_ALIAS",
)


class ResolutionError(Exception):
    """Typed domain error. Machine-readable via `.code` and `.audit`."""

    code = "RESOLUTION_ERROR"

    def __init__(self, message: str, *, audit: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.audit = audit or {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": str(self),
            "audit": self.audit,
        }


class InvalidProfileError(ResolutionError):
    code = "INVALID_PROFILE"


class AliasCollisionError(ResolutionError):
    code = "AMBIGUOUS_ALIAS"


class AmbiguousHeaderError(ResolutionError):
    code = "AMBIGUOUS_HEADER"


class DuplicateIdentityError(ResolutionError):
    code = "DUPLICATE_IDENTITY"


class UnresolvedIdentityError(ResolutionError):
    code = "UNRESOLVED_IDENTITY"


class ResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ResolutionStatus
    decision: str
    reason: str
    input_identifier: str
    normalized_identifier: str
    candidates: list[str] = Field(default_factory=list)
    value: str | None = None
    profile_version: str = PROFILE_VERSION
    pipeline_stage: str
    timestamp: str
    code: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"

    @property
    def blocks_downstream(self) -> bool:
        return self.status != "VALID"

    def as_audit(self) -> dict[str, Any]:
        return self.model_dump()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_key(value: Any, *, casefold: bool = True) -> str:
    """Strip, collapse whitespace. Optional casefold. Does not invent a key."""
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split())
    if casefold:
        text = text.casefold()
    return text


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return normalize_key(value, casefold=False) == ""
    return False


def result(
    *,
    status: ResolutionStatus,
    reason: str,
    input_identifier: str,
    normalized_identifier: str = "",
    candidates: list[str] | None = None,
    value: str | None = None,
    pipeline_stage: str,
    profile_version: str = PROFILE_VERSION,
    code: str | None = None,
    decision: str | None = None,
) -> ResolutionResult:
    if decision is None:
        decision = {
            "VALID": "proceed",
            "AMBIGUOUS": "review",
            "INVALID_PROFILE": "stop",
            "UNRESOLVED": "review",
            "REVIEW_REQUIRED": "review",
        }[status]
    return ResolutionResult(
        status=status,
        decision=decision,
        reason=reason,
        input_identifier="" if input_identifier is None else str(input_identifier),
        normalized_identifier=normalized_identifier,
        candidates=list(candidates or []),
        value=value,
        profile_version=profile_version,
        pipeline_stage=pipeline_stage,
        timestamp=utc_now(),
        code=code or status,
    )
