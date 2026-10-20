from hypertube.core.handler.AbstractHandler import AbstractHandler


class ArrayGetItemHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)

        array = command.payload[0]
        if isinstance(command.payload[1], list):
            indexes = command.payload[1]
        else:
            indexes = command.payload[1:]

        result = array
        for index in indexes:
            result = result[index]
        return result
