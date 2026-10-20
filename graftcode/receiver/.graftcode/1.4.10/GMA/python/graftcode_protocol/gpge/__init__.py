"""GPGE error protocol package."""

from graftcode_protocol.gpge.error_protocol import (
    GpgeErrorCode,
    GpgePublicError,
    format_coded_message,
    format_reason_phrase,
    format_template,
    format_wire_message,
    map_gpge_error,
    resolve,
)

__all__ = [
    "GpgeErrorCode",
    "GpgePublicError",
    "format_coded_message",
    "format_reason_phrase",
    "format_template",
    "format_wire_message",
    "map_gpge_error",
    "resolve",
]
