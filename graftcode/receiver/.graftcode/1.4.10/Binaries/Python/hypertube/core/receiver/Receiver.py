import sys
import traceback

from hypertube.core.interpreter.Interpreter import Interpreter
from hypertube.core.protocol.CommandSerializer import CommandSerializer
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeLogger import RuntimeLogger
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.connectionData.InMemoryConnectionData import InMemoryConnectionData
from hypertube.utils.connectionData.IConnectionData import IConnectionData
from hypertube.utils.exception.ExceptionSerializer import ExceptionSerializer
from hypertube.utils.messageHelper.MessageHelper import MessageHelper


class Receiver:
    _original_excepthook = None
    _exception_handler_initialized = False

    @staticmethod
    def initialize_exception_handler():
        """Initialize the global exception handler. Should be called once."""
        try:
            if not Receiver._exception_handler_initialized:
                # Store the original excepthook
                Receiver._original_excepthook = sys.excepthook

                # Set up global exception handler
                def custom_excepthook(exc_type, exc_value, exc_traceback):
                    # Format the exception
                    exception_string = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                    # Send to App Insights
                    MessageHelper.send_message_to_app_insights_sync("SdkUnhandledException", exception_string)
                    print("Hypertube unhandled exception: " + exception_string, file=sys.stderr)
                    # Call the original handler
                    if Receiver._original_excepthook:
                        Receiver._original_excepthook(exc_type, exc_value, exc_traceback)

                # Register the custom exception handler
                sys.excepthook = custom_excepthook
                Receiver._exception_handler_initialized = True
        except Exception as ex:
            print("Failed to initialize exception handler: {}".format(str(ex)))


    @staticmethod
    def send_command(message_byte_array, connection_data: IConnectionData = None):
        """
        Process a command message and return the response.

        Args:
            message_byte_array: The byte array containing the command message.
            connection_data: Optional connection data. If None, uses InMemoryConnectionData.

        Returns:
            bytearray: The response byte array.
        """
        Receiver.initialize_exception_handler()
        if connection_data is None:
            connection_data = InMemoryConnectionData()
        
        try:
            result = Interpreter.process(message_byte_array)
            return bytearray(CommandSerializer.serialize(result, connection_data))
        except Exception as ex:
            exception_command = ExceptionSerializer.serialize_exception(
                ex,
                Command(RuntimeName.python, CommandType.Exception, [])
            )
            return bytearray(CommandSerializer.serialize(exception_command, connection_data))

    @staticmethod
    def heart_beat(message_byte_array):
        """
        Process a heartbeat message and return the response.

        Args:
            message_byte_array: The byte array containing the heartbeat message.

        Returns:
            bytearray: The response byte array.
        """
        response_byte_array = bytearray(2)
        response_byte_array[0] = message_byte_array[11]
        response_byte_array[1] = message_byte_array[12] - 2
        return response_byte_array


    @staticmethod
    def get_runtime_info():
        """
        Get runtime information.

        Returns:
            str: Runtime information string.
        """
        return RuntimeLogger().get_runtime_info()

