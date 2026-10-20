import struct

from hypertube.utils import Command, CommandType, RuntimeName
from hypertube.utils.StringEncodingMode import StringEncodingMode


class TypeDeserializer:
    """Static utility — do not instantiate."""

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a static utility class and cannot be instantiated")

    @staticmethod
    def deserialize_command(encoded_command ):
        return Command(RuntimeName(encoded_command[0]), CommandType(encoded_command[1]), [])

    @staticmethod
    def deserialize_string(string_encoding_mode, encoded_string):
        if string_encoding_mode == StringEncodingMode.ASCII:
            return bytearray(encoded_string).decode('ascii')
        if string_encoding_mode == StringEncodingMode.UTF8:
            return bytearray(encoded_string).decode('utf-8')
        if string_encoding_mode == StringEncodingMode.UTF16:
            return bytearray(encoded_string).decode('utf-16')
        if string_encoding_mode == StringEncodingMode.UTF32:
            return bytearray(encoded_string).decode('utf-32')

        raise IndexError("String encoding mode out of range")

    @staticmethod
    def deserialize_int(encoded_int):
        return struct.unpack("<i", bytearray(encoded_int))[0]
    
    @staticmethod
    def deserialize_bool(encoded_bool):
        return struct.unpack("<?", bytearray(encoded_bool))[0]
    
    @staticmethod
    def deserialize_float(encoded_float):
        return struct.unpack("<f", bytearray(encoded_float))[0]

    @staticmethod
    def deserialize_byte(encoded_byte):
        return struct.unpack("<B", bytearray(encoded_byte))[0]
    
    @staticmethod
    def deserialize_char(encoded_char):
        return struct.unpack("<b", bytearray(encoded_char))[0]

    @staticmethod
    def deserialize_longlong(encoded_longlong):
        return struct.unpack("<q", bytearray(encoded_longlong))[0]

    @staticmethod
    def deserialize_double(encoded_double):
        return struct.unpack("<d", bytearray(encoded_double))[0]

    @staticmethod
    def deserialize_ullong(encoded_unsigned_longlong):
        return struct.unpack("<Q", bytearray(encoded_unsigned_longlong))[0]

    @staticmethod
    def deserialize_uint(encoded_unsigned_int):
        return struct.unpack("<I", bytearray(encoded_unsigned_int))[0]

    @staticmethod
    def deserialize_none(encoded_none):
        return None

    @staticmethod
    def deserialize_undefined(encoded_undefined):
        return None

    # Offset-based helpers below read straight from the original buffer via
    # struct.unpack_from, avoiding the buffer[p:p+n] slice + bytearray copy
    # used by the methods above (kept for backward compatibility).

    @staticmethod
    def deserialize_int_at(buffer, offset):
        return struct.unpack_from("<i", buffer, offset)[0]

    @staticmethod
    def deserialize_bool_at(buffer, offset):
        return struct.unpack_from("<?", buffer, offset)[0]

    @staticmethod
    def deserialize_float_at(buffer, offset):
        return struct.unpack_from("<f", buffer, offset)[0]

    @staticmethod
    def deserialize_byte_at(buffer, offset):
        return struct.unpack_from("<B", buffer, offset)[0]

    @staticmethod
    def deserialize_char_at(buffer, offset):
        return struct.unpack_from("<b", buffer, offset)[0]

    @staticmethod
    def deserialize_longlong_at(buffer, offset):
        return struct.unpack_from("<q", buffer, offset)[0]

    @staticmethod
    def deserialize_double_at(buffer, offset):
        return struct.unpack_from("<d", buffer, offset)[0]

    @staticmethod
    def deserialize_ullong_at(buffer, offset):
        return struct.unpack_from("<Q", buffer, offset)[0]

    @staticmethod
    def deserialize_uint_at(buffer, offset):
        return struct.unpack_from("<I", buffer, offset)[0]
