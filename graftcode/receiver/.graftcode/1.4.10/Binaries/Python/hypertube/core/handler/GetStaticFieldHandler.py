import inspect

from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class GetStaticFieldHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)
        clazz = command.payload[0]
        field_name = command.payload[1]
        try:
            return LazyModuleLoader.safe_getattr(clazz, field_name)
        except AttributeError:
            fields = []
            for available_field_name in dir(clazz):
                try:
                    value = inspect.getattr_static(clazz, available_field_name)
                except AttributeError:
                    continue
                if not callable(value):
                    fields.append(available_field_name)

            message = "Field {} not found in class {}. Available fields:\n{}".format(
                field_name,
                clazz.__name__,
                "\n".join(fields),
            )
            raise AttributeError(message) from None
