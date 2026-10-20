from hypertube.core.handler.AbstractHandler import AbstractHandler


class ArrayHandler(AbstractHandler):
    def process(self, command):
        try:
            processedArray = command.payload
            return processedArray

        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
