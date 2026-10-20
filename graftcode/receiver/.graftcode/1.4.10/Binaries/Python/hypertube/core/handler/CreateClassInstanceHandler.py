from hypertube.core.handler.AbstractHandler import AbstractHandler


class CreateClassInstanceHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)
            clazz = command.payload[0]
            if len(command.payload) > 1:
                method_arguments = command.payload[1:]
                return clazz(*method_arguments)
            return clazz()
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
