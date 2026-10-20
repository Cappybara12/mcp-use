"""Cross-runtime catalog of parsable type names.

The same identifiers are listed in every protocol binding so consumers can
membership-check without branching on runtime.
"""

from __future__ import annotations

from typing import Final, Mapping, Optional

_PARSED_DATETIME: Final[str] = "PARSED_DATETIME"
_PARSED_DATETIME_OFFSET: Final[str] = "PARSED_DATETIME_OFFSET"
_PARSED_TIME: Final[str] = "PARSED_TIME"
_PARSED_DURATION: Final[str] = "PARSED_DURATION"
_PARSED_UUID: Final[str] = "PARSED_UUID"
_PARSED_URI: Final[str] = "PARSED_URI"
_PARSED_POINT: Final[str] = "PARSED_POINT"
_PARSED_COLOR: Final[str] = "PARSED_COLOR"

PARSABLE_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "Date",
        "System.DateTime",
        "System.DateTimeOffset",
        "URL",
        "java.awt.Color",
        "java.awt.Point",
        "java.net.URI",
        "java.time.Duration",
        "java.time.Instant",
        "java.time.LocalTime",
        "java.time.OffsetDateTime",
        "java.util.UUID",
        "System.Drawing.Color",
        "System.Drawing.Point",
        "datetime.datetime",
        "datetime.timedelta",
        "datetime.time",
        "System.Guid",
        "System.TimeOnly",
        "System.TimeSpan",
        "System.Uri",
        "uuid.UUID",
    }
)

_FOREIGN_TO_CATEGORY: Final[Mapping[str, str]] = {
    "Date": _PARSED_DATETIME,
    "System.DateTime": _PARSED_DATETIME,
    "java.time.Instant": _PARSED_DATETIME,
    "datetime.datetime": _PARSED_DATETIME,
    "System.DateTimeOffset": _PARSED_DATETIME_OFFSET,
    "java.time.OffsetDateTime": _PARSED_DATETIME_OFFSET,
    "java.time.LocalTime": _PARSED_TIME,
    "System.TimeOnly": _PARSED_TIME,
    "datetime.time": _PARSED_TIME,
    "java.time.Duration": _PARSED_DURATION,
    "System.TimeSpan": _PARSED_DURATION,
    "datetime.timedelta": _PARSED_DURATION,
    "java.util.UUID": _PARSED_UUID,
    "System.Guid": _PARSED_UUID,
    "uuid.UUID": _PARSED_UUID,
    "java.net.URI": _PARSED_URI,
    "System.Uri": _PARSED_URI,
    "URL": _PARSED_URI,
    "java.awt.Point": _PARSED_POINT,
    "System.Drawing.Point": _PARSED_POINT,
    "java.awt.Color": _PARSED_COLOR,
    "System.Drawing.Color": _PARSED_COLOR,
}

_CATEGORY_TO_LOCAL: Final[Mapping[str, str]] = {
    _PARSED_DATETIME: "datetime.datetime",
    _PARSED_DATETIME_OFFSET: "datetime.datetime",
    _PARSED_TIME: "datetime.time",
    _PARSED_DURATION: "datetime.timedelta",
    _PARSED_UUID: "uuid.UUID",
}


def map_to_local_type(foreign_type: Optional[str]) -> str:
    """Map any cross-runtime parsable type name to the idiomatic Python type.

    Returns an empty string when the input is blank or not a recognized
    parsable type, or when Python has no idiomatic equivalent in the catalog
    (URI, point, and color groups).
    """
    if foreign_type is None or not foreign_type.strip():
        return ""
    category = _FOREIGN_TO_CATEGORY.get(foreign_type.strip())
    if category is None:
        return ""
    return _CATEGORY_TO_LOCAL.get(category, "")
