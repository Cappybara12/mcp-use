"""Python docstring type emission helpers for CommentDoc."""

from __future__ import annotations

import re
from typing import Optional

from graftcode_protocol.commentdoc.type_mapping import normalized_to_python_type

_PYTHON_CONTAINER_RAW = re.compile(
    r"^(?:typing\.)?(?:List|list|Tuple|tuple|Set|set|FrozenSet|frozenset|"
    r"Dict|dict|Mapping|mapping|Sequence|sequence|Iterable|iterable)\[",
    re.IGNORECASE,
)

_CONTAINER_HEADS = frozenset(
    {
        "list",
        "tuple",
        "set",
        "frozenset",
        "dict",
        "mapping",
        "sequence",
        "iterable",
    }
)


def is_python_container_raw(raw_type: str) -> bool:
    """Return True when *raw_type* is a Python container annotation (e.g. ``List[str]``)."""
    raw = raw_type.strip()
    if not raw:
        return False
    if _PYTHON_CONTAINER_RAW.match(raw):
        return True
    bracket = raw.find("[")
    if bracket <= 0:
        return False
    head = raw[:bracket].strip().lower()
    if "." in head:
        head = head.rsplit(".", 1)[-1]
    return head in _CONTAINER_HEADS


def emit_python_doc_type(
    raw_type: Optional[str], normalized_type: Optional[str]
) -> str:
    """Prefer native Python container syntax in docstrings; fall back to normalized mapping."""
    raw = (raw_type or "").strip()
    if raw and is_python_container_raw(raw):
        return raw
    return normalized_to_python_type(raw_type, normalized_type)
