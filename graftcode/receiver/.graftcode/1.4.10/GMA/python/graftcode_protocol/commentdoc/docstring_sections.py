"""Shared docstring section parsers for CommentDoc (Python Google/reST)."""

from __future__ import annotations

import re
from typing import List, Tuple

_SEE_ALSO_GOOGLE = re.compile(
    r"(?:^|\n)\s*See Also:\s*\n((?:[ \t]+.+\n?)*)",
    re.IGNORECASE,
)
_SEE_ALSO_RST = re.compile(
    r"\.\.\ seealso::\s*(.+?)(?=\n\S|\n\.\.|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def strip_see_also_from_description(description: str) -> str:
    """Remove a trailing Google-style ``See Also:`` block from *description*."""
    if not description:
        return description
    match = _SEE_ALSO_GOOGLE.search(description)
    if not match:
        return description
    return description[: match.start()].rstrip()


def parse_google_see_also_block(block: str) -> List[Tuple[str, str, str]]:
    """Parse indented lines under ``See Also:`` into ``(target, label, kind)`` tuples."""
    links: List[Tuple[str, str, str]] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ":" in stripped:
            target, _, label = stripped.partition(":")
            links.append((target.strip(), label.strip(), "seealso"))
        else:
            links.append((stripped, "", "seealso"))
    return links


def extract_see_also_links(raw_doc: str) -> List[Tuple[str, str, str]]:
    """Extract See Also links from Google-style and reST ``.. seealso::`` sections."""
    links: List[Tuple[str, str, str]] = []
    for match in _SEE_ALSO_RST.finditer(raw_doc):
        target = match.group(1).strip()
        if target:
            links.append((target, "", "seealso"))
    google_match = _SEE_ALSO_GOOGLE.search(raw_doc)
    if google_match:
        links.extend(parse_google_see_also_block(google_match.group(1)))
    return links
