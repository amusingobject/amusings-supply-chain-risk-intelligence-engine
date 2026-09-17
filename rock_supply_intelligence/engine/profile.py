"""Strict alias/profile validation and fail-closed alias resolution.

A malformed alias entry invalidates the whole profile. One alias to many
canonicals is AMBIGUOUS. There is no first-match fallback.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rock_supply_intelligence.engine.resolution import (
    InvalidProfileError,
    PROFILE_VERSION,
    ResolutionResult,
    is_blank,
    normalize_key,
    result,
)

PROFILE_STAGE = "profile_validation"


class FieldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical: str
    aliases: list[Any] = Field(default_factory=list)


class AliasProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    version: str = PROFILE_VERSION
    casefold: bool = True
    fields: list[FieldSpec]
    # Optional explicit unique priority: alias -> canonical. Must itself be valid
    # and may only name a canonical already in fields. Absent = no precedence.
    priority: dict[str, str] | None = None


class ValidatedAliasIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    version: str
    casefold: bool
    # normalized alias -> exactly one canonical
    alias_to_canonical: dict[str, str]
    canonicals: list[str]
    # optional explicit priority, already validated
    priority: dict[str, str] = Field(default_factory=dict)


def validate_alias_profile(raw: Any) -> ValidatedAliasIndex:
    """Validate an entire profile. Never drops bad entries and continues."""
    if not isinstance(raw, (AliasProfile, dict)):
        raise InvalidProfileError(
            "malformed nested profile: expected object",
            audit={"type": type(raw).__name__, "pipeline_stage": PROFILE_STAGE},
        )
    if isinstance(raw, dict):
        raw = _normalize_raw_profile(raw)
    try:
        profile = raw if isinstance(raw, AliasProfile) else AliasProfile.model_validate(raw)
    except InvalidProfileError:
        raise
    except Exception as exc:
        raise InvalidProfileError(
            f"malformed profile: {exc}",
            audit={"pipeline_stage": PROFILE_STAGE, "reason": "schema_or_type_error"},
        ) from exc

    if is_blank(profile.profile_id):
        raise InvalidProfileError("blank profile_id", audit={"pipeline_stage": PROFILE_STAGE})
    if not profile.fields:
        raise InvalidProfileError("profile has no fields", audit={"pipeline_stage": PROFILE_STAGE})

    canonicals: list[str] = []
    seen_canonical: dict[str, str] = {}
    alias_to_canonical: dict[str, str] = {}

    for spec in profile.fields:
        if not isinstance(spec.canonical, str) or is_blank(spec.canonical):
            raise InvalidProfileError(
                "blank canonical identifier",
                audit={"canonical": spec.canonical, "pipeline_stage": PROFILE_STAGE},
            )
        if not isinstance(spec.aliases, list):
            raise InvalidProfileError(
                "aliases must be a list",
                audit={"canonical": spec.canonical, "pipeline_stage": PROFILE_STAGE},
            )
        for item in spec.aliases:
            if not isinstance(item, str) or is_blank(item):
                raise InvalidProfileError(
                    "malformed or blank alias entry",
                    audit={
                        "alias": item,
                        "canonical": spec.canonical,
                        "reason": "blank_or_non_string_alias",
                        "pipeline_stage": PROFILE_STAGE,
                    },
                )
        canon_key = normalize_key(spec.canonical, casefold=profile.casefold)
        if not canon_key:
            raise InvalidProfileError(
                "blank canonical identifier",
                audit={"canonical": spec.canonical, "pipeline_stage": PROFILE_STAGE},
            )
        if canon_key in seen_canonical:
            raise InvalidProfileError(
                "duplicate canonical identifier",
                audit={
                    "canonical": spec.canonical,
                    "duplicate_of": seen_canonical[canon_key],
                    "pipeline_stage": PROFILE_STAGE,
                },
            )
        seen_canonical[canon_key] = spec.canonical
        canonicals.append(spec.canonical)
        # Canonical token also resolves to itself.
        _put_alias(alias_to_canonical, spec.canonical, spec.canonical, profile.casefold)
        for alias in spec.aliases:
            _put_alias(alias_to_canonical, alias, spec.canonical, profile.casefold)

    priority: dict[str, str] = {}
    if profile.priority:
        if not isinstance(profile.priority, dict):
            raise InvalidProfileError(
                "priority must be an object of alias -> canonical",
                audit={"pipeline_stage": PROFILE_STAGE},
            )
        for alias, canonical in profile.priority.items():
            if not isinstance(alias, str) or not isinstance(canonical, str):
                raise InvalidProfileError(
                    "malformed priority entry",
                    audit={"alias": alias, "canonical": canonical, "pipeline_stage": PROFILE_STAGE},
                )
            if is_blank(alias) or is_blank(canonical):
                raise InvalidProfileError(
                    "blank alias or canonical in priority rule",
                    audit={"alias": alias, "canonical": canonical, "pipeline_stage": PROFILE_STAGE},
                )
            key = normalize_key(alias, casefold=profile.casefold)
            mapped = alias_to_canonical.get(key)
            if mapped is None:
                raise InvalidProfileError(
                    "priority rule names an unknown alias",
                    audit={"alias": alias, "pipeline_stage": PROFILE_STAGE},
                )
            if normalize_key(canonical, casefold=profile.casefold) != normalize_key(
                mapped, casefold=profile.casefold
            ):
                raise InvalidProfileError(
                    "priority rule contradicts alias mapping",
                    audit={
                        "alias": alias,
                        "priority_canonical": canonical,
                        "mapped_canonical": mapped,
                        "pipeline_stage": PROFILE_STAGE,
                    },
                )
            priority[key] = mapped

    return ValidatedAliasIndex(
        profile_id=profile.profile_id,
        version=profile.version,
        casefold=profile.casefold,
        alias_to_canonical=alias_to_canonical,
        canonicals=canonicals,
        priority=priority,
    )


def _normalize_raw_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept fields[], aliases[{alias,canonical}], or mapping{alias: canonical}."""
    if "fields" in raw:
        return raw
    data = dict(raw)
    entries = data.pop("aliases", None)
    mapping = data.pop("mapping", None)
    grouped: dict[str, list[str]] = {}
    if entries is not None:
        if not isinstance(entries, list):
            raise InvalidProfileError(
                "malformed list/object structure: aliases must be a list",
                audit={"pipeline_stage": PROFILE_STAGE},
            )
        for item in entries:
            if not isinstance(item, dict):
                raise InvalidProfileError(
                    "malformed alias object",
                    audit={"entry": item, "pipeline_stage": PROFILE_STAGE, "code": "MALFORMED_ALIAS"},
                )
            alias = item.get("alias", item.get("from"))
            canonical = item.get("canonical", item.get("target", item.get("to")))
            if "canonical" not in item and "target" not in item and "to" not in item:
                raise InvalidProfileError(
                    "alias missing target",
                    audit={"alias": alias, "pipeline_stage": PROFILE_STAGE, "code": "MALFORMED_ALIAS"},
                )
            if is_blank(canonical):
                raise InvalidProfileError(
                    "alias entry with null/empty target",
                    audit={"alias": alias, "pipeline_stage": PROFILE_STAGE, "code": "MALFORMED_ALIAS"},
                )
            if not isinstance(alias, str) or is_blank(alias):
                raise InvalidProfileError(
                    "blank alias",
                    audit={"alias": alias, "canonical": canonical, "pipeline_stage": PROFILE_STAGE},
                )
            grouped.setdefault(str(canonical), []).append(alias)
    if mapping is not None:
        if not isinstance(mapping, dict):
            raise InvalidProfileError(
                "malformed mapping object",
                audit={"pipeline_stage": PROFILE_STAGE},
            )
        for alias, canonical in mapping.items():
            if is_blank(canonical):
                raise InvalidProfileError(
                    "alias entry with null/empty target",
                    audit={"alias": alias, "pipeline_stage": PROFILE_STAGE},
                )
            grouped.setdefault(str(canonical), []).append(alias)
    data["fields"] = [{"canonical": canon, "aliases": aliases} for canon, aliases in grouped.items()]
    return data


def _put_alias(
    table: dict[str, str],
    alias: str,
    canonical: str,
    casefold: bool,
) -> None:
    key = normalize_key(alias, casefold=casefold)
    if not key:
        raise InvalidProfileError(
            "blank alias",
            audit={"alias": alias, "canonical": canonical, "pipeline_stage": PROFILE_STAGE},
        )
    existing = table.get(key)
    if existing is not None and normalize_key(existing, casefold=casefold) != normalize_key(
        canonical, casefold=casefold
    ):
        raise InvalidProfileError(
            "duplicate alias assigned inconsistently",
            audit={
                "alias": alias,
                "canonical_a": existing,
                "canonical_b": canonical,
                "pipeline_stage": PROFILE_STAGE,
                "code": "AMBIGUOUS_ALIAS",
            },
        )
    table[key] = canonical


def try_validate_alias_profile(raw: Any) -> tuple[ValidatedAliasIndex | None, ResolutionResult]:
    try:
        index = validate_alias_profile(raw)
    except InvalidProfileError as exc:
        audit = exc.audit or {}
        status = "AMBIGUOUS" if audit.get("code") == "AMBIGUOUS_ALIAS" or "duplicate alias" in str(exc) else "INVALID_PROFILE"
        return None, result(
            status=status,  # type: ignore[arg-type]
            reason=str(exc),
            input_identifier=str(audit.get("alias") or audit.get("canonical") or ""),
            candidates=[str(audit[k]) for k in ("canonical_a", "canonical_b") if k in audit],
            pipeline_stage=PROFILE_STAGE,
            profile_version=str(audit.get("version") or PROFILE_VERSION),
            code=str(audit.get("code") or exc.code),
        )
    return index, result(
        status="VALID",
        reason="profile_valid",
        input_identifier=index.profile_id,
        pipeline_stage=PROFILE_STAGE,
        profile_version=index.version,
    )


def resolve_alias(index: ValidatedAliasIndex, token: Any) -> ResolutionResult:
    """Resolve one alias. 0 matches = UNRESOLVED, 1 = VALID, 2+ = AMBIGUOUS."""
    if not isinstance(token, str) and token is not None:
        return result(
            status="INVALID_PROFILE",
            reason="unsupported_field_type",
            input_identifier=repr(token),
            pipeline_stage="alias_resolution",
            profile_version=index.version,
            code="MALFORMED_ALIAS",
        )
    raw = "" if token is None else token
    key = normalize_key(raw, casefold=index.casefold)
    if not key:
        return result(
            status="UNRESOLVED",
            reason="blank_alias",
            input_identifier=raw,
            normalized_identifier=key,
            pipeline_stage="alias_resolution",
            profile_version=index.version,
            code="BLANK_IDENTITY",
        )
    mapped = index.alias_to_canonical.get(key)
    if mapped is None:
        return result(
            status="UNRESOLVED",
            reason="unresolved_alias",
            input_identifier=raw,
            normalized_identifier=key,
            pipeline_stage="alias_resolution",
            profile_version=index.version,
            code="UNRESOLVED",
        )
    return result(
        status="VALID",
        reason="unique_canonical_match",
        input_identifier=raw,
        normalized_identifier=key,
        candidates=[mapped],
        value=mapped,
        pipeline_stage="alias_resolution",
        profile_version=index.version,
    )
