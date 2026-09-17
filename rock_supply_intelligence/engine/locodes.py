"""Deterministic place matching for the POC fixture set.

Resolution order: exact UN/LOCODE, then trusted alias table. Ambiguous names
remain unresolved. This table is versioned with the contract; it is not a
geocoder.
"""

from __future__ import annotations

from dataclasses import dataclass

from rock_supply_intelligence.engine.resolution import InvalidProfileError, ResolutionResult, is_blank, result

TABLE_VERSION = "locodes-v0.1"


@dataclass(frozen=True)
class Place:
    locode: str
    name: str
    country: str
    kind: str
    aliases: tuple[str, ...]


PLACES: tuple[Place, ...] = (
    Place("TWKEL", "Keelung", "TW", "port", ("keelung", "chilung", "基隆", "twkel")),
    Place("TWKHH", "Kaohsiung", "TW", "port", ("kaohsiung", "高雄", "twkhh")),
    Place("TWTXG", "Taichung", "TW", "port", ("taichung", "台中", "臺中", "twtxg")),
    Place("TWTPE", "Taipei", "TW", "city", ("taipei", "台北", "臺北", "tpe")),
    Place("TWHUN", "Hualien", "TW", "port", ("hualien", "花蓮")),
    Place("USLGB", "Long Beach", "US", "port", ("long beach", "uslgb", "lgb")),
    Place("USLAX", "Los Angeles", "US", "port", ("los angeles", "la", "uslax", "lax")),
    Place("USBAL", "Baltimore", "US", "port", ("baltimore", "usbal")),
    Place("USNYC", "New York", "US", "port", ("new york", "nyc", "usnyc", "newark", "usewr")),
    Place("USSEA", "Seattle", "US", "port", ("seattle", "ussea")),
    Place("USTIW", "Tacoma", "US", "port", ("tacoma", "ustiw")),
    Place("USHOU", "Houston", "US", "port", ("houston", "ushou")),
    Place("USCHI", "Chicago", "US", "city", ("chicago", "ord", "uschi")),
    Place("USPHX", "Phoenix", "US", "city", ("phoenix", "phx")),
    Place("USDEN", "Denver", "US", "city", ("denver", "den")),
    Place("PAPCN", "Panama Canal", "PA", "canal", ("panama", "panama canal", "colon", "balboa", "papcn")),
    Place("EGSUZ", "Suez", "EG", "canal", ("suez", "suez canal", "port said", "egsuz")),
    Place("CNYTN", "Yantian", "CN", "port", ("yantian", "cnytn", "深圳盐田", "鹽田")),
    Place("CNSHA", "Shanghai", "CN", "port", ("shanghai", "cnsha", "上海")),
    Place("CAVAN", "Vancouver", "CA", "port", ("vancouver", "cavan")),
    Place("AEJEA", "Jebel Ali", "AE", "port", ("jebel ali", "dubai", "aejea")),
    Place("REDSEA", "Red Sea", "XX", "waterway", ("red sea", "bab el-mandeb", "gulf of aden")),
)


def normalize_token(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _place_keys(place: Place) -> tuple[str, ...]:
    keys = {place.locode.lower(), normalize_token(place.name), place.locode.lower().replace(" ", "")}
    for alias in place.aliases:
        token = normalize_token(alias)
        if token:
            keys.add(token)
            keys.add(token.replace(" ", ""))
    return tuple(keys)


def _build_place_index(places: tuple[Place, ...]) -> dict[str, tuple[Place, ...]]:
    buckets: dict[str, list[Place]] = {}
    for place in places:
        for key in _place_keys(place):
            buckets.setdefault(key, [])
            if all(existing.locode != place.locode for existing in buckets[key]):
                buckets[key].append(place)
    return {key: tuple(hits) for key, hits in buckets.items()}


PLACE_INDEX = _build_place_index(PLACES)


def validate_place_table(places: tuple[Place, ...] = PLACES) -> None:
    """Built-in aliases must be unique. Collisions are a profile error, not first-match."""
    index = _build_place_index(places)
    collisions = {key: hits for key, hits in index.items() if len(hits) > 1}
    if collisions:
        sample = next(iter(collisions.items()))
        raise InvalidProfileError(
            "place alias collision in locode table",
            audit={
                "alias": sample[0],
                "canonical_a": sample[1][0].locode,
                "canonical_b": sample[1][1].locode,
                "code": "AMBIGUOUS_ALIAS",
                "pipeline_stage": "locode_table",
            },
        )


validate_place_table()


def resolve_place_result(value: str | None) -> ResolutionResult:
    if value is not None and not isinstance(value, str):
        return result(
            status="INVALID_PROFILE",
            reason="unsupported_field_type",
            input_identifier=repr(value),
            pipeline_stage="locode_resolution",
            profile_version=TABLE_VERSION,
            code="MALFORMED_ALIAS",
        )
    if is_blank(value):
        return result(
            status="UNRESOLVED",
            reason="blank_place_token",
            input_identifier="" if value is None else value,
            pipeline_stage="locode_resolution",
            profile_version=TABLE_VERSION,
            code="BLANK_IDENTITY",
        )
    token = normalize_token(value)
    compact = token.replace(" ", "")
    hits = PLACE_INDEX.get(token) or PLACE_INDEX.get(compact) or ()
    locodes = tuple(dict.fromkeys(p.locode for p in hits))
    if len(locodes) > 1:
        return result(
            status="AMBIGUOUS",
            reason="ambiguous_place_alias",
            input_identifier=value or "",
            normalized_identifier=token,
            candidates=list(locodes),
            pipeline_stage="locode_resolution",
            profile_version=TABLE_VERSION,
            code="AMBIGUOUS_ALIAS",
        )
    if len(locodes) == 1:
        return result(
            status="VALID",
            reason="unique_place_match",
            input_identifier=value or "",
            normalized_identifier=token,
            candidates=[locodes[0]],
            value=locodes[0],
            pipeline_stage="locode_resolution",
            profile_version=TABLE_VERSION,
        )
    return result(
        status="UNRESOLVED",
        reason="unresolved_place",
        input_identifier=value or "",
        normalized_identifier=token,
        pipeline_stage="locode_resolution",
        profile_version=TABLE_VERSION,
        code="UNRESOLVED",
    )


def resolve_place(value: str | None) -> Place | None:
    resolved = resolve_place_result(value)
    if not resolved.is_valid or not resolved.value:
        return None
    for place in PLACES:
        if place.locode == resolved.value:
            return place
    return None


def same_place(a: str | None, b: str | None) -> bool:
    """True only when both tokens uniquely resolve to the same locode.

    Unresolved or ambiguous tokens are not treated as a match, even if the
    raw strings are equal. That string-equality fallback was fail-open.
    """
    pa = resolve_place_result(a)
    pb = resolve_place_result(b)
    if pa.blocks_downstream or pb.blocks_downstream:
        return False
    return bool(pa.value) and pa.value == pb.value


def locode_of(value: str | None) -> str | None:
    resolved = resolve_place_result(value)
    if resolved.blocks_downstream:
        return None
    return resolved.value
