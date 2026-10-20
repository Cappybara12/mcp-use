import struct

from hypertube.utils.Type import Type
from hypertube.utils.StringEncodingMode import StringEncodingMode


class TypeSerializer:
    """Static utility — do not instantiate."""

    # Pre-built once and reused by write_primitive to avoid re-packing on every call.
    _NONE_BYTES = struct.pack("<BBB", Type.HypertubeNoneType.value, 1, 0)

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a static utility class and cannot be instantiated")

    @staticmethod
    def write_command_header(stream, command):
        """Write a command header directly to a binary stream (e.g. io.BytesIO)."""
        stream.write(struct.pack("<BiBB", Type.Command.value, len(command.payload),
                                  command.runtime_name.value, command.command_type.value))

    @staticmethod
    def write_primitive(stream, payload_item):
        """Write a primitive value directly to a binary stream (e.g. io.BytesIO)."""
        if payload_item is None:
            stream.write(TypeSerializer._NONE_BYTES)
        elif isinstance(payload_item, bool):
            TypeSerializer.write_bool(stream, payload_item)
        elif isinstance(payload_item, int):
            if payload_item in range(-2 ** 31, 2 ** 31):
                TypeSerializer.write_int(stream, payload_item)
            elif payload_item in range(-2 ** 63, 2 ** 63):
                TypeSerializer.write_longlong(stream, payload_item)
            else:
                TypeSerializer.write_ullong(stream, payload_item)
        elif isinstance(payload_item, float):
            TypeSerializer.write_double(stream, payload_item)
        elif isinstance(payload_item, str):
            TypeSerializer.write_string(stream, payload_item)
        else:
            raise TypeError(f"Unsupported payload item type: {type(payload_item)} for payload item: {payload_item}.")

    @staticmethod
    def write_string(stream, string_value):
        encoded_string = string_value.encode('utf-8')
        stream.write(struct.pack("<BBi", Type.HypertubeString.value, StringEncodingMode.UTF8.value,
                                  len(encoded_string)))
        stream.write(encoded_string)

    @staticmethod
    def write_int(stream, int_value):
        stream.write(struct.pack("<BBi", Type.HypertubeInteger.value, 4, int_value))

    @staticmethod
    def write_bool(stream, bool_value):
        stream.write(struct.pack("<BB?", Type.HypertubeBoolean.value, 1, bool_value))

    @staticmethod
    def write_float(stream, float_value):
        stream.write(struct.pack("<BBf", Type.HypertubeFloat.value, 4, float_value))

    @staticmethod
    def write_byte(stream, byte_value):
        stream.write(struct.pack("<BBB", Type.HypertubeByte.value, 1, byte_value))

    @staticmethod
    def write_char(stream, char_value):
        stream.write(struct.pack("<BBb", Type.HypertubeChar.value, 1, char_value))

    @staticmethod
    def write_longlong(stream, longlong_value):
        stream.write(struct.pack("<BBq", Type.HypertubeLongLong.value, 8, longlong_value))

    @staticmethod
    def write_double(stream, double_value):
        stream.write(struct.pack("<BBd", Type.HypertubeDouble.value, 8, double_value))

    @staticmethod
    def write_ullong(stream, ullong_value):
        stream.write(struct.pack("<BBQ", Type.HypertubeUnsignedLongLong.value, 8, ullong_value))

    @staticmethod
    def write_uint(stream, uint_value):
        stream.write(struct.pack("<BBI", Type.HypertubeUnsignedInteger.value, 4, uint_value))

    @staticmethod
    def write_none(stream):
        stream.write(TypeSerializer._NONE_BYTES)
