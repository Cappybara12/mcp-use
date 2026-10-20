"""Cross-runtime exception category mapping for ``COMMENT_THROW`` payloads.

The mapping is sourced **verbatim** from the Hypertube SDK -- the same
SDK that GMA and GCG already use as their runtime bridge. Re-using
Hypertube's ``ExceptionType`` enum guarantees that whatever category we
emit into the UGM here will be re-throwable on the other side of the
bridge with zero translation work; cross-runtime exception fidelity
falls out of the existing infrastructure for free.

Wire contract
-------------
``COMMENT_THROW.payload``::

    [raw_type, category, description]

* ``raw_type`` -- the source-language class name (string), preserved
  for documentation and fallback rendering.
* ``category`` -- one of the names from :data:`CATEGORY_NAMES` if the
  raw type is recognized, or ``""`` otherwise.
* ``description`` -- free-form text (neutral markup, see
  ``inline_markup``).

The 9 categories below mirror Hypertube's ``ExceptionType`` enum 0-8.
.NET adds 4 extra plugin-system codes (9-12); those are deliberately
**not** re-exported here because they are not portable across runtimes
and we never want them to appear in cross-runtime UGM payloads.

ASCII diagram of the round-trip
-------------------------------
::

    source.py        UGM (neutral)              target.cs
    -----------     -----------------          ----------------
    ValueError ---> raw_to_category --+
                                      v
                          "ILLEGAL_ARGUMENT_EXCEPTION"
                                      |
                                      +--> category_to_idiomatic
                                                              |
                                                              v
                                                  ArgumentException
"""

from __future__ import annotations

from typing import Final, Mapping

# Canonical category names (mirrors Hypertube ExceptionType 0-8).
EXCEPTION: Final[str] = "EXCEPTION"
IO_EXCEPTION: Final[str] = "IO_EXCEPTION"
FILE_NOT_FOUND_EXCEPTION: Final[str] = "FILE_NOT_FOUND_EXCEPTION"
RUNTIME_EXCEPTION: Final[str] = "RUNTIME_EXCEPTION"
ARITHMETIC_EXCEPTION: Final[str] = "ARITHMETIC_EXCEPTION"
ILLEGAL_ARGUMENT_EXCEPTION: Final[str] = "ILLEGAL_ARGUMENT_EXCEPTION"
INDEX_OUT_OF_BOUNDS_EXCEPTION: Final[str] = "INDEX_OUT_OF_BOUNDS_EXCEPTION"
NULL_POINTER_EXCEPTION: Final[str] = "NULL_POINTER_EXCEPTION"
DIVIDE_BY_ZERO_EXCEPTION: Final[str] = "DIVIDE_BY_ZERO_EXCEPTION"

CATEGORY_NAMES: Final[frozenset[str]] = frozenset(
    {
        EXCEPTION,
        IO_EXCEPTION,
        FILE_NOT_FOUND_EXCEPTION,
        RUNTIME_EXCEPTION,
        ARITHMETIC_EXCEPTION,
        ILLEGAL_ARGUMENT_EXCEPTION,
        INDEX_OUT_OF_BOUNDS_EXCEPTION,
        NULL_POINTER_EXCEPTION,
        DIVIDE_BY_ZERO_EXCEPTION,
    }
)

# Source-side classification table.
#
# Sourced from Hypertube
# ``src/python/hypertube/utils/ExceptionType.py::to_enum`` (Python-side
# ``ExceptionSerializer.getExceptionCode`` equivalent). Bare class names
# only -- callers strip module prefixes before lookup so both
# ``ValueError`` and ``builtins.ValueError`` resolve identically.
_RAW_TO_CATEGORY: Final[Mapping[str, str]] = {
    "Exception": EXCEPTION,
    "IOError": IO_EXCEPTION,
    "OSError": IO_EXCEPTION,
    "FileNotFoundError": FILE_NOT_FOUND_EXCEPTION,
    "RuntimeError": RUNTIME_EXCEPTION,
    "ArithmeticError": ARITHMETIC_EXCEPTION,
    # Python has no first-class "IllegalArgument" exception; ValueError
    # and TypeError cover the same role (rejecting argument shapes).
    # We map ValueError -> ILLEGAL_ARGUMENT and keep TypeError ->
    # NULL_POINTER for parity with PHP's TypeError mapping.
    "ValueError": ILLEGAL_ARGUMENT_EXCEPTION,
    "IndexError": INDEX_OUT_OF_BOUNDS_EXCEPTION,
    "KeyError": INDEX_OUT_OF_BOUNDS_EXCEPTION,
    "AttributeError": NULL_POINTER_EXCEPTION,
    "TypeError": NULL_POINTER_EXCEPTION,
    "ZeroDivisionError": DIVIDE_BY_ZERO_EXCEPTION,
}

# Target-side rendering table.
#
# Sourced from Hypertube
# ``src/python/hypertube/utils/exception/ExceptionThrower.py`` (the
# ``to_exception`` enum->class mapping). ``ILLEGAL_ARGUMENT_EXCEPTION``
# falls back to ``ValueError`` (Hypertube's table has no entry; we use
# the Pythonic equivalent of Java's IllegalArgumentException).
_CATEGORY_TO_IDIOMATIC: Final[Mapping[str, str]] = {
    EXCEPTION: "Exception",
    IO_EXCEPTION: "IOError",
    FILE_NOT_FOUND_EXCEPTION: "FileNotFoundError",
    RUNTIME_EXCEPTION: "RuntimeError",
    ARITHMETIC_EXCEPTION: "ArithmeticError",
    ILLEGAL_ARGUMENT_EXCEPTION: "ValueError",
    INDEX_OUT_OF_BOUNDS_EXCEPTION: "IndexError",
    NULL_POINTER_EXCEPTION: "AttributeError",
    DIVIDE_BY_ZERO_EXCEPTION: "ZeroDivisionError",
}


def raw_to_category(raw_type: str | None) -> str:
    """Classify a source-language exception name into a canonical category.

    Returns ``""`` when the raw type is not recognized so the caller can
    leave ``COMMENT_THROW.payload[1]`` empty and let GCG fall back to
    the raw spelling in ``payload[0]``.
    """
    if not raw_type:
        return ""
    bare = raw_type.strip().split(".")[-1]
    return _RAW_TO_CATEGORY.get(bare, "")


def category_to_idiomatic(category: str | None) -> str:
    """Render a canonical category as the idiomatic Python class name."""
    if not category:
        return ""
    return _CATEGORY_TO_IDIOMATIC.get(category, "")
