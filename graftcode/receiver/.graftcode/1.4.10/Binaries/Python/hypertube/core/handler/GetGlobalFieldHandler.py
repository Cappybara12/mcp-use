from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.LazyModuleLoader import LazyModuleLoader


class GetGlobalFieldHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        self.validate(command, self._required_parameters_count, "GetGlobalField")

        full_field_name = command.payload[0]
        if not isinstance(full_field_name, str) or "." not in full_field_name:
            raise Exception("Invalid field name format. Expected 'module_name.field_name'.")

        module_name, field_name = full_field_name.rsplit(".", 1)

        try:
            module = LazyModuleLoader.get_module(module_name)
            if module is None:
                raise ImportError(f"Could not import module '{module_name}'.")
        except ImportError as e:
            raise ImportError(f"Could not import module '{module_name}'.") from e

        try:
            value = getattr(module, field_name)
        except AttributeError as e:
            try:
                available = [
                    attr for attr in dir(module)
                    if not callable(getattr(module, attr, None)) and not attr.startswith("__")
                ]
            except Exception:
                available = []
            message = (
                    f"Field '{field_name}' not found in module '{module_name}'. "
                    "Available non-callable attributes:\n" + "\n".join(available)
            )
            raise AttributeError(message) from e

        return value
