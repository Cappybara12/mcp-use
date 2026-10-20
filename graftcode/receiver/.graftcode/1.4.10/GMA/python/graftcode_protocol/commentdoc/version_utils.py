"""Version string helpers for CommentDoc parsing and emission."""

from __future__ import annotations

import re

_VERSION_PATTERN = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:\.\d+)?$")


def looks_like_version(value: str) -> bool:
    """Return True when *value* looks like a semantic version (e.g. ``1.2.3``)."""
    return bool(_VERSION_PATTERN.match(value.strip()))
