import array as _array_module

from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType


_ARRAY_LIKE_TYPES = (list, tuple, bytes, bytearray, memoryview, _array_module.array)


class RetrieveArrayHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            response = command.payload[0]
            if isinstance(response, _ARRAY_LIKE_TYPES):
                payload = response if isinstance(response, list) else list(response)
                return Command(
                    command.runtime_name,
                    CommandType.Array,
                    self._to_nested_payload(payload, command.runtime_name),
                )

            raise Exception("Invalid argument type for RetrieveArrayHandler. Expected an array.")
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None

    @staticmethod
    def _to_nested_payload(items, runtime_name):
        payload = []
        for item in items:
            if isinstance(item, list):
                payload.append(
                    Command(
                        runtime_name,
                        CommandType.Array,
                        RetrieveArrayHandler._to_nested_payload(item, runtime_name),
                    )
                )
            else:
                payload.append(item)
        return payload
