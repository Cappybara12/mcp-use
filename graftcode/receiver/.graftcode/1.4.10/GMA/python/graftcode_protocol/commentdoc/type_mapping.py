from __future__ import annotations

import re
from typing import Final, Mapping, Optional

from graftcode_protocol.commentdoc.normalized_type import NormalizedType

_PYTHON_RAW_TO_NORMALIZED: Final[Mapping[str, NormalizedType]] = {
    "str": NormalizedType.STRING,
    "string": NormalizedType.STRING,
    "int": NormalizedType.INTEGER,
    "integer": NormalizedType.INTEGER,
    "long": NormalizedType.INTEGER,
    "float": NormalizedType.NUMBER,
    "double": NormalizedType.NUMBER,
    "complex": NormalizedType.NUMBER,
    "decimal": NormalizedType.NUMBER,
    "bool": NormalizedType.BOOLEAN,
    "boolean": NormalizedType.BOOLEAN,
    "true": NormalizedType.BOOLEAN,
    "false": NormalizedType.BOOLEAN,
    "datetime": NormalizedType.DATETIME,
    "date": NormalizedType.DATE,
    "time": NormalizedType.DATETIME,
    "timedelta": NormalizedType.DATETIME,
    "uuid": NormalizedType.STRING,
    "enum": NormalizedType.ENUM,
    "list": NormalizedType.ARRAY,
    "tuple": NormalizedType.ARRAY,
    "set": NormalizedType.ARRAY,
    "frozenset": NormalizedType.ARRAY,
    "sequence": NormalizedType.ARRAY,
    "dict": NormalizedType.MAP,
    "mapping": NormalizedType.MAP,
    "any": NormalizedType.UNKNOWN,
    "object": NormalizedType.OBJECT,
    "none": NormalizedType.VOID,
    "nonetype": NormalizedType.VOID,
    "void": NormalizedType.VOID,
    "bytes": NormalizedType.STRING,
    "bytearray": NormalizedType.STRING,
    "bytesio": NormalizedType.STRING,
    "uploadfile": NormalizedType.OBJECT,
    "exception": NormalizedType.ERROR,
    "baseexception": NormalizedType.ERROR,
}

_ARRAY_CONTAINER_HEADS: Final[frozenset[str]] = frozenset(
    {
        "list",
        "tuple",
        "set",
        "frozenset",
        "sequence",
        "iterable",
    }
)

_MAP_CONTAINER_HEADS: Final[frozenset[str]] = frozenset(
    {
        "dict",
        "mapping",
    }
)

_PYTHON_WRAPPER_TYPES: Final[frozenset[str]] = frozenset(
    {
        "optional",
        "union",
        "awaitable",
        "coroutine",
        "future",
        "list",
        "sequence",
        "iterable",
        "tuple",
        "set",
        "frozenset",
        "dict",
        "mapping",
        "callable",
    }
)


def _pick_non_null_union_member(raw: str) -> str:
    if "|" not in raw and not raw.strip().startswith("Union["):
        return raw
    if raw.strip().startswith("Union["):
        inner = raw[raw.index("[") + 1 : raw.rindex("]")]
        members = [member.strip() for member in inner.split(",")]
    else:
        members = [member.strip() for member in raw.split("|")]
    nullish = {"none", "nonetype", "null"}
    for member in members:
        head = member.split("[", 1)[0].strip().lower()
        if head not in nullish:
            return member
    return members[0] if members else raw


def _unwrap_python_wrapper(raw: str) -> str:
    trimmed = raw.strip()
    bracket = trimmed.find("[")
    if bracket <= 0:
        return trimmed
    head = trimmed[:bracket].strip().lower()
    if head not in _PYTHON_WRAPPER_TYPES:
        return trimmed
    depth = 0
    start = bracket + 1
    for index, char in enumerate(trimmed[start:], start=start):
        if char == "[":
            depth += 1
        elif char == "]":
            if depth == 0:
                return _unwrap_python_wrapper(trimmed[start:index].strip())
            depth -= 1
        elif char == "," and depth == 0:
            return _unwrap_python_wrapper(trimmed[start:index].strip())
    return trimmed


def _container_head(raw: str) -> Optional[str]:
    trimmed = raw.strip()
    bracket = trimmed.find("[")
    if bracket <= 0:
        return None
    head = trimmed[:bracket].strip().lower()
    if "." in head:
        head = head.rsplit(".", 1)[-1]
    return head


def _extract_lookup_key(raw_type: Optional[str]) -> Optional[str]:
    if raw_type is None or not str(raw_type).strip():
        return None
    canonical = _pick_non_null_union_member(str(raw_type).strip())
    container = _container_head(canonical)
    if container in _ARRAY_CONTAINER_HEADS:
        return NormalizedType.ARRAY.value
    if container in _MAP_CONTAINER_HEADS:
        return NormalizedType.MAP.value
    canonical = _unwrap_python_wrapper(canonical)
    if canonical.endswith("[]"):
        return NormalizedType.ARRAY.value
    head = re.split(r"[|&\s\[]", canonical, maxsplit=1)[0]
    head = head.replace("?", "").strip().lstrip(".")
    if "." in head:
        head = head.rsplit(".", 1)[-1]
    return head.lower()


def resolve_normalized_type(raw_type: Optional[str]) -> Optional[NormalizedType]:
    lookup_key = _extract_lookup_key(raw_type)
    if lookup_key == NormalizedType.ARRAY.value:
        return NormalizedType.ARRAY
    if lookup_key == NormalizedType.MAP.value:
        return NormalizedType.MAP
    if lookup_key is None:
        return None
    return _PYTHON_RAW_TO_NORMALIZED.get(lookup_key)


def python_raw_to_normalized(raw_type: Optional[str]) -> str:
    resolved = resolve_normalized_type(raw_type)
    return resolved.value if resolved is not None else ""


def normalized_to_python_type(
    raw_type: Optional[str], normalized_type: Optional[str]
) -> str:
    return NormalizedType.normalized_to_python_type(raw_type, normalized_type)
