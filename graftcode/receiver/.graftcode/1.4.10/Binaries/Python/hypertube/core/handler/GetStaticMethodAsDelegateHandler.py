from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class GetStaticMethodAsDelegateHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, "InvokeStaticMethod")

            clazz = command.payload[0]
            try:
                method = LazyModuleLoader.safe_getattr(clazz, command.payload[1])
            except AttributeError:
                methods = [method for method in dir(clazz) if callable(LazyModuleLoader.safe_getattr(clazz, method))]
                message = "Method {} not found in class {}. Available methods:\n".format(command.payload[1],
                                                                                         clazz.__name__)
                for method in methods:
                    message += "{}\n".format(method)
                raise AttributeError(message)

            return method
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None


