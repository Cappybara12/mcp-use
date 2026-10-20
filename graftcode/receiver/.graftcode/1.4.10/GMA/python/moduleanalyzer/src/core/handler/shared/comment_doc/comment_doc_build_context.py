"""Context passed to CommentDoc section handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from docstring_parser import Docstring


@dataclass(frozen=True)
class CommentDocBuildContext:
    """Parsed docstring plus reflection context for section builders."""

    analyzed_object: Any
    raw_doc: str
    parsed: Docstring
    emit_code_examples: bool
