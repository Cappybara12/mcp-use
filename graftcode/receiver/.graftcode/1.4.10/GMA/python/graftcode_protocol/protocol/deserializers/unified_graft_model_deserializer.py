from __future__ import annotations

from typing import Any, List, Optional

from graftcode_protocol.protocol.deserializers.type_deserializer import TypeDeserializer
from graftcode_protocol.enums.graft_code_primitive_type import GraftCodePrimitiveType
from graftcode_protocol.enums.string_encoding_mode import StringEncodingMode
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class UnifiedGraftModelDeserializer:
    position = 0
    buffer = []
    command = 0
    buffer_len = 0

    def __init__(self, buffer: List[int], buffer_len: Optional[int] = None) -> None:
        self.buffer = buffer
        self.buffer_len = buffer_len if buffer_len is not None else len(buffer)
        self.command = UnifiedGraftModel(
            RuntimeName(buffer[0]), UnifiedGraftModelType(buffer[10]), []
        )
        self.position = 11

    def is_at_end(self) -> bool:
        return self.position == self.buffer_len

    def deserialize(self) -> UnifiedGraftModel:
        while not self.is_at_end():
            self.command = self.command.add_arg_to_payload(
                self.read_object(self.buffer[self.position])
            )
        return self.command

    def read_object(self, type_num: int) -> Any:
        type_value = GraftCodePrimitiveType(type_num)
        switch = {
            GraftCodePrimitiveType.GRAFT_MODEL: self.read_command,
            GraftCodePrimitiveType.STRING: self.read_string,
            GraftCodePrimitiveType.INTEGER: self.read_int,
            GraftCodePrimitiveType.BOOLEAN: self.read_bool,
            GraftCodePrimitiveType.FLOAT: self.read_float,
            GraftCodePrimitiveType.BYTE: self.read_byte,
            GraftCodePrimitiveType.CHAR: self.read_char,
            GraftCodePrimitiveType.LONG: self.read_longlong,
            GraftCodePrimitiveType.DOUBLE: self.read_double,
            GraftCodePrimitiveType.UNSIGNED_LONG_LONG: self.read_ullong,
            GraftCodePrimitiveType.UNSIGNED_INTEGER: self.read_uint,
        }
        return switch.get(type_value, lambda: Exception("Type not supported"))()

    def read_command(self) -> UnifiedGraftModel:
        p = self.position
        number_of_elements_in_payload = TypeDeserializer.deserialize_int(
            self.buffer[p + 1 : p + 5]
        )
        runtime = self.buffer[p + 5]
        command_type = self.buffer[p + 6]
        self.position += 7

        payload = [
            self.read_object(self.buffer[self.position])
            for _ in range(number_of_elements_in_payload)
        ]

        return UnifiedGraftModel(
            RuntimeName(runtime), UnifiedGraftModelType(command_type), payload
        )

    def read_string(self) -> str:
        p = self.position
        string_encoding_mode = StringEncodingMode(self.buffer[p + 1])
        size = TypeDeserializer.deserialize_int(self.buffer[p + 2 : p + 6])
        self.position += 6
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_string(
            string_encoding_mode, self.buffer[p : p + size]
        )

    def read_int(self) -> int:
        size = 4
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_int(self.buffer[p : p + size])

    def read_bool(self) -> bool:
        size = 1
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_bool(self.buffer[p : p + size])

    def read_float(self) -> float:
        size = 4
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_float(self.buffer[p : p + size])

    def read_byte(self) -> int:
        size = 1
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_byte(self.buffer[p : p + size])

    def read_char(self) -> int:
        size = 1
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_char(self.buffer[p : p + size])

    def read_longlong(self) -> int:
        size = 8
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_longlong(self.buffer[p : p + size])

    def read_double(self) -> float:
        size = 8
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_double(self.buffer[p : p + size])

    def read_ullong(self) -> int:
        size = 8
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_ullong(self.buffer[p : p + size])

    def read_uint(self) -> int:
        size = 4
        self.position += 2
        p = self.position
        self.position += size
        return TypeDeserializer.deserialize_uint(self.buffer[p : p + size])
