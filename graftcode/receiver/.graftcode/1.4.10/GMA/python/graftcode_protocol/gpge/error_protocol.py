"""Cross-runtime GPGE error protocol."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

WIRE_PREFIX = "GRAFT"
MAX_REASON_PHRASE_LENGTH = 200
_WIRE_MESSAGE_PATTERN = re.compile(r"^\[GRAFT:([A-Z0-9_]+)\]\s*(.*)$")


class GpgeErrorCode(str, Enum):
    INTERNAL_ERROR = "INTERNAL_ERROR"
    FRAMEWORK_TYPE_IN_PUBLIC_API = "FRAMEWORK_TYPE_IN_PUBLIC_API"
    UNSUPPORTED_TECHNOLOGY = "UNSUPPORTED_TECHNOLOGY"
    PACKAGE_NOT_FOUND = "PACKAGE_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass(frozen=True)
class _ErrorDefinition:
    http_status: int
    message_template: str
    exception_types: tuple[str, ...]
    message_patterns: tuple[str, ...]


@dataclass(frozen=True)
class GpgePublicError:
    code: GpgeErrorCode
    http_status: int
    public_message: str


_DEFINITIONS: dict[GpgeErrorCode, _ErrorDefinition] = {
    GpgeErrorCode.FRAMEWORK_TYPE_IN_PUBLIC_API: _ErrorDefinition(
        422,
        "Using complex types from framework in public interfaces is not supported yet. Type used {0}",
        ("UnsupportedTypeUsageException",),
        ("using complex types from framework in public interfaces",),
    ),
    GpgeErrorCode.UNSUPPORTED_TECHNOLOGY: _ErrorDefinition(
        422,
        "The requested technology is not supported for this graft operation.",
        ("NotSupportedException",),
        (
            "not supported",
            "unsupported",
            "not yet supported",
            "not yet supported by gpge",
            "is not supported for getting original package name",
            "no compilation for",
        ),
    ),
    GpgeErrorCode.PACKAGE_NOT_FOUND: _ErrorDefinition(
        404,
        "The requested package or version was not found.",
        ("FileNotFoundException",),
        ("no ugm file found", "package not found"),
    ),
    GpgeErrorCode.INVALID_REQUEST: _ErrorDefinition(
        400,
        "The package request is invalid.",
        ("ArgumentException", "ArgumentNullException", "InvalidOperationException"),
        ("invalid package", "cannot be null", "malformed", "parse error"),
    ),
    GpgeErrorCode.SERVICE_UNAVAILABLE: _ErrorDefinition(
        503,
        "The graft service is busy. Please try again shortly.",
        (),
        ("service saturated", "too many concurrent", "timeout", "unavailable", "overloaded"),
    ),
    GpgeErrorCode.INTERNAL_ERROR: _ErrorDefinition(
        500,
        "Package generation failed. Please try again later.",
        (),
        (),
    ),
}


_MESSAGE_INFERENCE_ORDER: tuple[GpgeErrorCode, ...] = (
    GpgeErrorCode.FRAMEWORK_TYPE_IN_PUBLIC_API,
    GpgeErrorCode.UNSUPPORTED_TECHNOLOGY,
    GpgeErrorCode.INVALID_REQUEST,
    GpgeErrorCode.PACKAGE_NOT_FOUND,
    GpgeErrorCode.SERVICE_UNAVAILABLE,
)


def format_wire_message(code: GpgeErrorCode, public_message: str) -> str:
    return f"[{WIRE_PREFIX}:{code.value}] {public_message}"


def format_template(code: GpgeErrorCode, *args: Any) -> str:
    template = _DEFINITIONS[code].message_template
    if not args:
        return template
    try:
        return template.format(*args)
    except (IndexError, ValueError):
        return template


def format_coded_message(code: GpgeErrorCode, *args: Any) -> str:
    return format_wire_message(code, format_template(code, *args))


def try_parse_wire_message(message: str | None) -> tuple[GpgeErrorCode, str] | None:
    if not message:
        return None
    match = _WIRE_MESSAGE_PATTERN.match(message.strip())
    if not match:
        return None
    try:
        code = GpgeErrorCode(match.group(1))
    except ValueError:
        return None
    return code, match.group(2).strip()


def resolve(error: BaseException | None) -> GpgePublicError:
    if error is None:
        return _to_public_error(
            GpgeErrorCode.INTERNAL_ERROR,
            _DEFINITIONS[GpgeErrorCode.INTERNAL_ERROR].message_template,
        )

    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parsed = try_parse_wire_message(str(current))
        if parsed and parsed[0] != GpgeErrorCode.INTERNAL_ERROR:
            return _to_public_error(parsed[0], parsed[1])
        current = current.__cause__

    inferred = _try_infer_code(error)
    if inferred is not None:
        return inferred

    return _to_public_error(
        GpgeErrorCode.INTERNAL_ERROR,
        _DEFINITIONS[GpgeErrorCode.INTERNAL_ERROR].message_template,
    )


def resolve_from_message(message: str | None) -> GpgePublicError:
    if not message:
        return _to_public_error(
            GpgeErrorCode.INTERNAL_ERROR,
            _DEFINITIONS[GpgeErrorCode.INTERNAL_ERROR].message_template,
        )

    parsed = try_parse_wire_message(message)
    if parsed and parsed[0] != GpgeErrorCode.INTERNAL_ERROR:
        return _to_public_error(parsed[0], parsed[1])

    lower_message = _first_line(message).lower()
    for code in _MESSAGE_INFERENCE_ORDER:
        definition = _DEFINITIONS[code]
        if any(pattern in lower_message for pattern in definition.message_patterns):
            return _to_public_error(code, _build_inferred_public_message(code, message))

    return _to_public_error(
        GpgeErrorCode.INTERNAL_ERROR,
        _DEFINITIONS[GpgeErrorCode.INTERNAL_ERROR].message_template,
    )


def map_gpge_error(error: BaseException) -> tuple[str, int]:
    resolved = resolve(error)
    return resolved.public_message, resolved.http_status


def format_reason_phrase(public_message: str) -> str:
    single_line = _first_line(public_message)
    if not single_line:
        return "Graft package error"
    if len(single_line) <= MAX_REASON_PHRASE_LENGTH:
        return single_line
    return single_line[: MAX_REASON_PHRASE_LENGTH - 3] + "..."


def _try_infer_code(error: BaseException) -> GpgePublicError | None:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        type_name = current.__class__.__name__
        full_type_name = f"{current.__class__.__module__}.{type_name}"
        lower_message = _first_line(str(current)).lower()

        for code in _MESSAGE_INFERENCE_ORDER:
            definition = _DEFINITIONS[code]
            if _matches_definition(definition, type_name, full_type_name, lower_message):
                return _to_public_error(code, _build_inferred_public_message(code, str(current)))
        current = current.__cause__
    return None


def _matches_definition(
    definition: _ErrorDefinition,
    type_name: str,
    full_type_name: str,
    lower_message: str,
) -> bool:
    for exception_type in definition.exception_types:
        if (
            type_name == exception_type
            or full_type_name.endswith("." + exception_type)
            or exception_type in full_type_name
        ):
            return True
    return any(pattern in lower_message for pattern in definition.message_patterns)


def _build_inferred_public_message(code: GpgeErrorCode, raw_message: str) -> str:
    if code == GpgeErrorCode.FRAMEWORK_TYPE_IN_PUBLIC_API:
        marker = "type used "
        index = raw_message.lower().find(marker)
        if index >= 0:
            type_name = _first_line(raw_message[index + len(marker) :])
            if type_name:
                return format_template(code, type_name)

    if code == GpgeErrorCode.INVALID_REQUEST and _is_safe_developer_message(raw_message):
        return _first_line(raw_message)

    return _DEFINITIONS[code].message_template


def _is_safe_developer_message(message: str) -> bool:
    first_line = _first_line(message)
    if not first_line:
        return False
    lower = first_line.lower()
    return (
        "azure" not in lower
        and "blob" not in lower
        and "exception" not in lower
        and "stack" not in lower
        and " at " not in lower
        and len(first_line) <= 240
    )


def _to_public_error(code: GpgeErrorCode, public_message: str) -> GpgePublicError:
    definition = _DEFINITIONS[code]
    message = _first_line(public_message) if public_message else definition.message_template
    return GpgePublicError(code=code, http_status=definition.http_status, public_message=message)


def _first_line(message: str) -> str:
    return message.splitlines()[0].strip() if message else ""
