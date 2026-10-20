from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class InvokeGlobalFunctionHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, "InvokeGlobalFunction")
        except ValueError as exc:
            raise ValueError(
                "InvokeGlobalFunction parameters mismatch. "
                "Expected at least a fully qualified function name (module.function)."
            ) from exc

        # The first payload parameter must be the fully qualified function name,
        # e.g. "my_module.my_function".
        full_function_name = command.payload[0]
        if "." not in full_function_name:
            raise ValueError(
                "Invalid function name format. "
                "Expected a fully qualified name like 'module_name.function_name'."
            )

        module_name, function_name = full_function_name.rsplit(".", 1)

        try:
            module = LazyModuleLoader.get_module(module_name)
            if module is None:
                raise ImportError(f"Could not import module '{module_name}'.")
        except ImportError as exc:
            raise ImportError(f"Could not import module '{module_name}'.") from exc

        try:
            function = getattr(module, function_name)
        except AttributeError as exc:
            available = [attr for attr in dir(module) if callable(getattr(module, attr))]
            message = (
                f"Function '{function_name}' not found in module '{module_name}'. "
                "Available functions:\n" + "\n".join(available)
            )
            raise AttributeError(message) from exc

        if not callable(function):
            raise TypeError(f"Attribute '{function_name}' in module '{module_name}' is not callable.")

        arguments, kwargs = self._split_arguments_and_kwargs(command.payload, 1)
        return function(*arguments, **kwargs)
