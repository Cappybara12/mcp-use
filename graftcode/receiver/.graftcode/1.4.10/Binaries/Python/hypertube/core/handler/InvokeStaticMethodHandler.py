from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class InvokeStaticMethodHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 2

    def process(self, command):
        self.validate(command, self._required_parameters_count, "InvokeStaticMethod")

        clazz = command.payload[0]
        try:
            method = LazyModuleLoader.safe_getattr(clazz, command.payload[1])
        except AttributeError:
            methods = [
                method_name
                for method_name in dir(clazz)
                if callable(LazyModuleLoader.safe_getattr(clazz, method_name))
            ]
            message = "Method {} not found in class {}. Available methods:\n{}".format(
                command.payload[1],
                clazz.__name__,
                "\n".join(methods),
            )
            raise AttributeError(message) from None

        arguments, kwargs = self._split_arguments_and_kwargs(command.payload, 2)
        return self.resolve_async_result(method(*arguments, **kwargs))


