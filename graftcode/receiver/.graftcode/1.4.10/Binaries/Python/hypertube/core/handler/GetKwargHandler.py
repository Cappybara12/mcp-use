from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.CommandType import CommandType


class GetKwargHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            # kwargs are passed as a list in the payload as "key1", "value1", "key2", "value2"
            if len(command.payload) % 2 != 0:
                raise Exception("GetKwargHandler parameters mismatch. Payload should contain an even number of elements.")

            kwargs = dict(zip(command.payload[::2], command.payload[1::2]))
            return (CommandType.AsKwargs, kwargs)


        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
