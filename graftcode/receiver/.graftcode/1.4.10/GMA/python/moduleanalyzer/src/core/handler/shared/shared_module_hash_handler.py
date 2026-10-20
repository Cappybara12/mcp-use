import inspect
from typing import Any, Union

from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class SharedModuleHashHandler:
    """
    Handler responsible for generating a unified graft model by returning the
    hash code of the module name where the analyzed object is defined.
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: UnifiedGraftModel,
        _handlers: Any,
    ) -> Union[str, int]:
        """
        Generates a unified graft model by determining the module in which the
        analyzed object is defined and returning the hash code of the module's
        name.

        :param analyzed_object: The object being analyzed, whose module name
                                hash is to be determined.
        :param _parent_command: The parent command related to the object
                                (unused, required by interface).
        :param _handlers: A collection of handlers (unused, required by interface).
        :return: The hash code of the module name, or "null" if the module
                 cannot be determined.
        """
        # Determine the module in which the analyzed object is defined
        module = inspect.getmodule(analyzed_object)

        # If the module or its name is None, return "null"
        if module is None or module.__name__ is None:
            return "null"

        # Return the hash code of the module's name
        return hash(module.__name__)
