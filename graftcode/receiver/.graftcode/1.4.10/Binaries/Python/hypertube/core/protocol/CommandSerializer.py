import io
import struct
from hypertube.core.protocol.TypeSerializer import TypeSerializer
from hypertube.core.referenceCache.ReferencesCache import ReferencesCache
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.TypesHandler import TypesHandler
from hypertube.utils.connectionData.IConnectionData import IConnectionData

# Reused instead of rebuilding a 7-byte "no connection data" placeholder on every call.
EMPTY_CONNECTION_DATA = bytes(7)

class CommandSerializer:
    """Static utility — do not instantiate."""

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a static utility class and cannot be instantiated")

    @staticmethod
    def serialize(root_command: Command, connection_data: IConnectionData, runtime_version=0):
        ms = io.BytesIO()

        ms.write(struct.pack("<BB", root_command.runtime_name.value, runtime_version))

        if connection_data is not None:
            ms.write(bytes(connection_data.serialize_connection_data()))
        else:
            ms.write(EMPTY_CONNECTION_DATA)

        ms.write(struct.pack("<BB", RuntimeName.python.value, root_command.command_type.value))

        CommandSerializer.serialize_recursively(root_command, ms)
        return ms.getvalue()

    @staticmethod
    def serialize_recursively(command: Command, ms: io.BytesIO):
        for item in command.get_payload():
            if isinstance(item, Command):
                TypeSerializer.write_command_header(ms, item)
                CommandSerializer.serialize_recursively(item, ms)
            elif TypesHandler.is_primitive_or_none(item):
                TypeSerializer.write_primitive(ms, item)
            else:
                cached_reference = ReferencesCache().cache_reference(item)
                ref_command = Command(RuntimeName.python, CommandType.Reference, [cached_reference])
                TypeSerializer.write_command_header(ms, ref_command)
                CommandSerializer.serialize_recursively(ref_command, ms)