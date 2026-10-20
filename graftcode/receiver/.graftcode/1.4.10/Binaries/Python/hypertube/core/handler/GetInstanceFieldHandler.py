from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class GetInstanceFieldHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)
            clazz = command.payload[0]
            field = command.payload[1]
            try:
                return LazyModuleLoader.safe_getattr(clazz, field)
            except AttributeError:
                fields = [field for field in dir(clazz) if not callable(LazyModuleLoader.safe_getattr(clazz, field))]
                message = "Field {} not found in class {}. Available fields:\n".format(field, clazz.__class__.__name__)
                for field in fields:
                    message += "{}\n".format(field)
                raise AttributeError(message)
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None

