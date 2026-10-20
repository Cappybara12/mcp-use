import os

from hypertube.core.handler.Handler import Handler
from hypertube.core.protocol.CommandDeserializer import CommandDeserializer
from hypertube.core.protocol.CommandSerializer import CommandSerializer
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.connectionData.IConnectionData import IConnectionData
from hypertube.utils.connectionData.Http2ConnectionData import Http2ConnectionData
from hypertube.utils.connectionData.WsConnectionData import WsConnectionData
from hypertube.utils.connectionData.InMemoryConnectionData import InMemoryConnectionData
from hypertube.utils.messageHelper.MessageHelper import MessageHelper


class Interpreter:
    debug_mode = (os.environ.get("HYPERTUBE_DEBUG") or "").lower() == "true"

    @staticmethod
    def execute(command, connection_data: IConnectionData):
        if Interpreter.debug_mode:
            Interpreter._log_debug("Command sent from calling side", command)

        message_byte_array = CommandSerializer.serialize(command, connection_data)

        if isinstance(connection_data, WsConnectionData):
            from hypertube.core.webSocketClient.WebSocketClient import WebSocketClient
            response_byte_array = WebSocketClient.send_message(connection_data, message_byte_array)
        elif isinstance(connection_data, Http2ConnectionData):
            from hypertube.core.http2Client.Http2Client import Http2Client
            response_byte_array = Http2Client.send_message(connection_data, message_byte_array)
        else:
            if len(connection_data.get_headers()) > 0:
                context_metadata_payload = Interpreter.build_context_metadata_payload(command, connection_data)
                command = Command(command.runtime_name, CommandType.ContextMetadata,
                                  [context_metadata_payload, command])
                message_byte_array = CommandSerializer.serialize(command, connection_data)

            if command.runtime_name == RuntimeName.python and isinstance(connection_data, InMemoryConnectionData):
                from hypertube.core.receiver.Receiver import Receiver
                response_byte_array = Receiver.send_command(message_byte_array)
            else:
                from hypertube.core.transmitter.Transmitter import Transmitter
                response_byte_array = Transmitter.send_command(message_byte_array, connection_data.get_config())

        response = CommandDeserializer.deserialize(response_byte_array)

        if Interpreter.debug_mode:
            Interpreter._log_debug("Command received on calling side", response)

        return response

    @staticmethod
    def process(message_byte_array):
        received_command = CommandDeserializer.deserialize(message_byte_array)

        if Interpreter.debug_mode:
            Interpreter._log_debug("Command received on called side", received_command)

        response = Handler.handle_command(received_command)

        if Interpreter.debug_mode:
            Interpreter._log_debug("Response sent from called side", response)

        return response

    @staticmethod
    def _log_debug(label, details):
        try:
            message = f"{label}: {details}"
            print(message)
            MessageHelper.send_message_to_app_insights("SdkMessage", message)
        except Exception:
            pass

    @staticmethod
    def build_context_metadata_payload(command, connection_data: IConnectionData):
        metadata_payload = []
        headers = connection_data.get_headers()

        for key, value in headers.items():
            metadata_payload.append(key)
            metadata_payload.append(value)

        return Command(command.runtime_name, CommandType.Array, metadata_payload)
