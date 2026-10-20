from hypertube.core.handler.AbstractHandler import AbstractHandler


class GetResultTypeHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)
        if command.payload[0] is None:
            return "null"
        return f"{command.payload[0].__class__.__module__}.{command.payload[0].__class__.__name__}"