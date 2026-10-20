from hypertube.core.handler.AbstractHandler import AbstractHandler

class ArrayGetSizeHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            array = command.payload[0]
            size = 1
            while(isinstance(array, list)):
                size = size * len(array)
                array = array[0]

            return size


        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
