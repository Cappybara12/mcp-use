from hypertube.core.handler.ArrayHandler import ArrayHandler
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.handler.GetTypeHandler import GetTypeHandler


class ContextMetadataHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 1
        self._get_type_handler = GetTypeHandler()
        self._array_handler = ArrayHandler()

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)

        get_type_command = Command(RuntimeName.python, CommandType.GetType, "graftcode.context.request_context.RequestContext")

        context_type = self._get_type_handler.process(get_type_command)

        if hasattr(context_type, "current") and callable(getattr(context_type, "current")):
            current_context = context_type.current()
        else:
            current_context = context_type()

        if not command.payload:
            raise Exception("Context metadata payload must contain an array command.")

        array_command = command.payload[0]

        if isinstance(array_command, Command) and array_command.command_type is CommandType.Array:
            values = self._array_handler.process(array_command)

            if len(values) % 2 != 0:
                raise Exception("Context metadata payload must contain key/value pairs.")

            headers = dict()
            for i in range(0, len(values), 2):
                key = values[i]
                if key is None or str(key).strip() == "":
                    raise Exception("Context metadata key cannot be null or empty.")
                raw_value = values[i + 1]
                headers[key] = raw_value

            if hasattr(current_context, "set_headers") and callable(getattr(current_context, "set_headers")):
                current_context.set_headers(headers)
            else:
                setattr(current_context, "headers", headers)
        else:
            raise Exception("Context metadata payload must be an array")

        return 0
