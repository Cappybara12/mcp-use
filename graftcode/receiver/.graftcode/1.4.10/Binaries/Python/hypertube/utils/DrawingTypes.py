"""Standard-library types for drawing and URI complex-type marshaling."""

from typing import NamedTuple
from urllib.parse import ParseResult, urlparse

# 2D point (same field layout as java.awt.Point / System.Drawing.Point payloads).
Point = NamedTuple('Point', [('x', int), ('y', int)])

# RGBA color (r, g, b, a); alias matches Java/System.Drawing color semantics.
Color = NamedTuple('RGBA', [('r', int), ('g', int), ('b', int), ('a', int)])



def color_channel(value: int) -> int:
    """Normalize an ARGB channel to unsigned int 0-255 for wire encoding."""
    return int(value) & 0xFF


__all__ = ['Point', 'Color', 'color_channel', 'ParseResult', 'urlparse']
