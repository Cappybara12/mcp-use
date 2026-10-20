from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.referenceCache.ReferencesCache import ReferencesCache
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName


class ResolveInstanceHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            if command.runtime_name == RuntimeName.python:
                return ReferencesCache().resolve_reference(command)
            else:
                Command(command.runtime_name, CommandType.Reference, command.payload[0])
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
