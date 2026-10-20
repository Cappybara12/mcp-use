from hypertube.core.handler.AbstractHandler import AbstractHandler


class ArraySetItemHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 3

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            data = command.payload[0]
            indexes_from_payload = command.payload[1]
            value = command.payload[2]

            if isinstance(indexes_from_payload, list):
                indexes = indexes_from_payload
            else:
                indexes = [indexes_from_payload]

            if isinstance(data, dict):
                data[indexes[0]] = value
            elif len(indexes) == 1:
                data[indexes[0]] = value
            else:
                current = data
                for i in range(len(indexes) - 1):
                    current = current[indexes[i]]
                current[indexes[-1]] = value

            return data

        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
