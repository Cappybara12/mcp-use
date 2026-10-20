from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class SetStaticFieldHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 3

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            clazz = command.payload[0]
            field = command.payload[1]
            new_value = command.payload[2]
            try:
                setattr(clazz, field, new_value)
            except AttributeError:
                fields = [field for field in dir(clazz) if not callable(LazyModuleLoader.safe_getattr(clazz, field))]
                message = "Field {} not found in class {}. Available fields:\n".format(field, clazz.__name__)
                for field in fields:
                    message += "{}\n".format(field)
                raise AttributeError(message)
            return clazz
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
