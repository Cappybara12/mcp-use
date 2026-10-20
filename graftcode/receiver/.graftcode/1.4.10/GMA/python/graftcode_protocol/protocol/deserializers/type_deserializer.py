from __future__ import annotations

import struct

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.string_encoding_mode import (
    StringEncodingMode,
)
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class TypeDeserializer:

    @staticmethod
    def deserialize_command(encoded_command: bytes) -> UnifiedGraftModel:
        return UnifiedGraftModel(
            RuntimeName(encoded_command[0]),
            UnifiedGraftModelType(encoded_command[1]),
            [],
        )

    @staticmethod
    def deserialize_string(
        string_encoding_mode: StringEncodingMode, encoded_string: bytes
    ) -> str:
        if string_encoding_mode == StringEncodingMode.ASCII:
            return bytearray(encoded_string).decode("ascii")
        if string_encoding_mode == StringEncodingMode.UTF8:
            return bytearray(encoded_string).decode("utf-8")
        if string_encoding_mode == StringEncodingMode.UTF16:
            return bytearray(encoded_string).decode("utf-16")
        if string_encoding_mode == StringEncodingMode.UTF32:
            return bytearray(encoded_string).decode("utf-32")

        raise IndexError("String encoding mode out of range")

    @staticmethod
    def deserialize_int(encoded_int: bytes) -> int:
        return struct.unpack("<i", bytearray(encoded_int))[0]

    @staticmethod
    def deserialize_bool(encoded_bool: bytes) -> bool:
        return struct.unpack("<?", bytearray(encoded_bool))[0]

    @staticmethod
    def deserialize_float(encoded_float: bytes) -> float:
        return struct.unpack("<f", bytearray(encoded_float))[0]

    @staticmethod
    def deserialize_byte(encoded_byte: bytes) -> int:
        return struct.unpack("<B", bytearray(encoded_byte))[0]

    @staticmethod
    def deserialize_char(encoded_char: bytes) -> int:
        return struct.unpack("<b", bytearray(encoded_char))[0]

    @staticmethod
    def deserialize_longlong(encoded_longlong: bytes) -> int:
        return struct.unpack("<q", bytearray(encoded_longlong))[0]

    @staticmethod
    def deserialize_double(encoded_double: bytes) -> float:
        return struct.unpack("<d", bytearray(encoded_double))[0]

    @staticmethod
    def deserialize_ullong(encoded_unsigned_longlong: bytes) -> int:
        return struct.unpack("<Q", bytearray(encoded_unsigned_longlong))[0]

    @staticmethod
    def deserialize_uint(encoded_unsigned_int: bytes) -> int:
        return struct.unpack("<I", bytearray(encoded_unsigned_int))[0]
