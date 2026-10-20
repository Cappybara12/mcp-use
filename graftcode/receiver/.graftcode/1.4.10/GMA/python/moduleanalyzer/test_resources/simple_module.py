"""
Simple Python module for basic testing scenarios.
Equivalent to simple-package/index.js in Node.js tests.
"""

from typing import Optional


class SimpleClass:
    """A simple class for basic testing."""

    class_variable = "simple_value"

    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        """Get the name."""
        return self.name

    def set_name(self, name: str) -> None:
        """Set the name."""
        self.name = name

    @staticmethod
    def static_method(value: int) -> int:
        """Simple static method."""
        return value * 2


def simple_function(a: int, b: int) -> int:
    """Simple global function."""
    return a + b


def function_with_optional(required: str, optional: Optional[str] = None) -> str:
    """Function with optional parameter."""
    if optional:
        return f"{required} - {optional}"
    return required


# Global variables
SIMPLE_CONSTANT = "CONSTANT_VALUE"
simple_variable = 100
simple_list = [1, 2, 3, 4, 5]
