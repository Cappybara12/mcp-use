import inspect
from typing import Any

from graftcode_protocol.enums.modifier_type import ModifierType


class SharedModifierHandler:
    """
    Handler for determining the modifier type of a given analyzed object.
    """

    def generate_unified_graft_model(
        self, analyzed_object: Any, _parent_command: Any, _handlers: Any
    ) -> int:
        """
        Determines the modifier type of the analyzed object based on its name.

        In Python, the naming convention for indicating the intended visibility of a method or attribute is as follows:
        - A single underscore `_` prefix (e.g., `_method`) indicates that the method or attribute is intended for
         internal use. It is a convention to signal that it is protected.
        - A double underscore `__` prefix (e.g., `__method`) triggers name mangling where the interpreter changes
         the name of the method or attribute to include the class name. This is used to avoid naming conflicts in
         subclasses and is intended to make the method or attribute private.

        Parameters:
        analyzed_object (object): The object being analyzed.
        _parent_command (object): The parent command object (unused).
        _handlers (object): The handlers object (unused).

        Returns:
        ModifierType: The determined modifier type (PUBLIC, PRIVATE, or PROTECTED).
        """
        # Handle string field names
        if isinstance(analyzed_object, str):
            name = analyzed_object
        elif inspect.isfunction(analyzed_object) or inspect.ismethod(analyzed_object):
            name = analyzed_object.__name__
        else:
            # For other objects, try to get __name__ or use string representation
            name = getattr(analyzed_object, "__name__", str(analyzed_object))

        # Special case: __init__ is the constructor and should be PUBLIC
        # In Python, constructors are always publicly accessible
        if name == "__init__":
            return ModifierType.PUBLIC.value

        if getattr(analyzed_object, "__isabstractmethod__", False):
            return ModifierType.PUBLIC.value

        # Determine modifier based on name
        if name.startswith("__"):
            return ModifierType.PRIVATE.value
        if name.startswith("_"):
            return ModifierType.PROTECTED.value
        return ModifierType.PUBLIC.value
