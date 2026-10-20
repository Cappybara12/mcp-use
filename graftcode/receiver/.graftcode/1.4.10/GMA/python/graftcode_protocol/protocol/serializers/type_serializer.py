from __future__ import annotations

import struct
from typing import Any, List

from graftcode_protocol.enums.graft_code_primitive_type import (
    GraftCodePrimitiveType,
)
from graftcode_protocol.enums.string_encoding_mode import (
    StringEncodingMode,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class TypeSerializer:

    @staticmethod
    def serialize_primitive(payload_item: Any) -> List[int]:
        if payload_item is None:
            return TypeSerializer.serialize_none()
        if isinstance(payload_item, bool):
            return TypeSerializer.serialize_bool(payload_item)
        elif isinstance(payload_item, int):
            if payload_item in range(-(2**31), 2**31):
                return TypeSerializer.serialize_int(payload_item)
            elif payload_item in range(-(2**63), 2**63):
                return TypeSerializer.serialize_longlong(payload_item)
            else:
                return TypeSerializer.serialize_ullong(payload_item)
        elif isinstance(payload_item, float):
            return TypeSerializer.serialize_double(payload_item)
        elif isinstance(payload_item, str):
            return TypeSerializer.serialize_string(payload_item)
        else:
            raise Exception(
                "Python: Type serialization not supported for type: "
                + str(type(payload_item))
            )

    @staticmethod
    def serialize_none() -> List[int]:
        """Serialize None/null value."""
        return [GraftCodePrimitiveType.NULL.value, 0]

    @staticmethod
    def serialize_command(command: UnifiedGraftModel) -> List[int]:
        length = list(bytearray(struct.pack("<i", len(command.payload))))
        return (
            [GraftCodePrimitiveType.GRAFT_MODEL.value]
            + length
            + [command.runtime_name.value, command.graft_model_type.value]
        )

    @staticmethod
    def serialize_string(string_value: str) -> List[int]:
        encoded_string_list = list(bytearray(string_value, "utf-8"))
        length = list(bytearray(struct.pack("<i", len(encoded_string_list))))
        return (
            [GraftCodePrimitiveType.STRING.value]
            + [StringEncodingMode.UTF8.value]
            + length
            + encoded_string_list
        )

    @staticmethod
    def serialize_int(int_value: int) -> List[int]:
        encoded_int_list = list(bytearray(struct.pack("<i", int_value)))
        length = len(encoded_int_list)
        return [
            GraftCodePrimitiveType.INTEGER.value,
            length,
        ] + encoded_int_list

    @staticmethod
    def serialize_bool(bool_value: bool) -> List[int]:
        encoded_bool_list = list(bytearray(struct.pack("?", bool_value)))
        length = len(encoded_bool_list)
        return [
            GraftCodePrimitiveType.BOOLEAN.value,
            length,
        ] + encoded_bool_list

    @staticmethod
    def serialize_float(float_value: float) -> List[int]:
        encoded_float_list = list(bytearray(struct.pack("<f", float_value)))
        length = len(encoded_float_list)
        return [
            GraftCodePrimitiveType.FLOAT.value,
            length,
        ] + encoded_float_list

    @staticmethod
    def serialize_byte(bytes_value: int) -> List[int]:
        encoded_byte_list = list(bytearray(struct.pack("<B", bytes_value)))
        length = len(encoded_byte_list)
        return [
            GraftCodePrimitiveType.BYTE.value,
            length,
        ] + encoded_byte_list

    @staticmethod
    def serialize_char(char_value: int) -> List[int]:
        encoded_char_list = list(bytearray(struct.pack("<b", char_value)))
        length = len(encoded_char_list)
        return [
            GraftCodePrimitiveType.CHAR.value,
            length,
        ] + encoded_char_list

    @staticmethod
    def serialize_longlong(longlong_value: int) -> List[int]:
        encoded_longlong_list = list(bytearray(struct.pack("<q", longlong_value)))
        length = len(encoded_longlong_list)
        return [
            GraftCodePrimitiveType.LONG.value,
            length,
        ] + encoded_longlong_list

    @staticmethod
    def serialize_double(double_value: float) -> List[int]:
        encoded_double_list = list(bytearray(struct.pack("<d", double_value)))
        length = len(encoded_double_list)
        return [
            GraftCodePrimitiveType.DOUBLE.value,
            length,
        ] + encoded_double_list

    @staticmethod
    def serialize_ullong(unsigned_longlong_value: int) -> List[int]:
        encoded_unsignedlonglong_list = list(
            bytearray(struct.pack("<Q", unsigned_longlong_value))
        )
        length = len(encoded_unsignedlonglong_list)
        return [
            GraftCodePrimitiveType.UNSIGNED_LONG_LONG.value,
            length,
        ] + encoded_unsignedlonglong_list

    @staticmethod
    def serialize_uint(unsigned_int_value: int) -> List[int]:
        encoded_unsigned_int_list = list(
            bytearray(struct.pack("<I", unsigned_int_value))
        )
        length = len(encoded_unsigned_int_list)
        return [
            GraftCodePrimitiveType.UNSIGNED_INTEGER.value,
            length,
        ] + encoded_unsigned_int_list
