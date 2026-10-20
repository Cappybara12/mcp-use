import struct

from hypertube.core.protocol.TypeDeserializer import TypeDeserializer
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.Type import Type
from hypertube.utils.StringEncodingMode import StringEncodingMode


class CommandDeserializer:
    """Static utility — do not instantiate."""

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a static utility class and cannot be instantiated")

    @staticmethod
    def deserialize(buffer):
        """
        Deserialize a command from a byte array.

        Args:
            buffer: The byte array containing the serialized command.

        Returns:
            Command: The deserialized command.
        """
        buffer_len = len(buffer)
        runtime_name = RuntimeName(buffer[0])
        command_type = CommandType(buffer[10])
        position = 11

        # Use a list to hold position (mutable reference for nested functions)
        pos_ref = [position]

        def is_at_end():
            return pos_ref[0] == buffer_len

        def read_object(type_num):
            type_value = Type(type_num)
            switch = {
                Type.Command: read_command,
                Type.HypertubeString: read_string,
                Type.HypertubeInteger: read_int,
                Type.HypertubeBoolean: read_bool,
                Type.HypertubeFloat: read_float,
                Type.HypertubeByte: read_byte,
                Type.HypertubeChar: read_char,
                Type.HypertubeLongLong: read_longlong,
                Type.HypertubeDouble: read_double,
                Type.HypertubeUnsignedLongLong: read_ullong,
                Type.HypertubeUnsignedInteger: read_uint,
                Type.HypertubeNoneType: read_none,
                Type.HypertubeUndefinedType: read_undefined
            }
            func = switch.get(type_value)
            if func is None:
                raise Exception("Type not supported")
            return func()

        def read_command():
            p = pos_ref[0]
            number_of_elements_in_payload = struct.unpack_from("<i", buffer, p + 1)[0]
            runtime = buffer[p + 5]
            command_type_value = buffer[p + 6]
            pos_ref[0] += 7

            payload = [
                read_object(buffer[pos_ref[0]])
                for _ in range(number_of_elements_in_payload)
            ]
            return Command(RuntimeName(runtime), CommandType(command_type_value), payload)

        def read_string():
            p = pos_ref[0]
            string_encoding_mode = StringEncodingMode(buffer[p + 1])
            size = TypeDeserializer.deserialize_int_at(buffer, p + 2)
            pos_ref[0] += 6
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_string(string_encoding_mode, buffer[p:p + size])

        def read_int():
            size = 4
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_int_at(buffer, p)

        def read_bool():
            size = 1
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_bool_at(buffer, p)

        def read_float():
            size = 4
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_float_at(buffer, p)

        def read_byte():
            size = 1
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_byte_at(buffer, p)

        def read_char():
            size = 1
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_char_at(buffer, p)

        def read_longlong():
            size = 8
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_longlong_at(buffer, p)

        def read_double():
            size = 8
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_double_at(buffer, p)

        def read_ullong():
            size = 8
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_ullong_at(buffer, p)

        def read_uint():
            size = 4
            pos_ref[0] += 2
            p = pos_ref[0]
            pos_ref[0] += size
            return TypeDeserializer.deserialize_uint_at(buffer, p)

        def read_none():
            pos_ref[0] += 3
            return TypeDeserializer.deserialize_none(None)

        def read_undefined():
            pos_ref[0] += 3
            return TypeDeserializer.deserialize_undefined(None)

        # Main deserialization loop: collect the payload into a list and
        # build the Command once, instead of rebuilding it on every element.
        payload = []
        while not is_at_end():
            payload.append(read_object(buffer[pos_ref[0]]))

        return Command(runtime_name, command_type, payload)
