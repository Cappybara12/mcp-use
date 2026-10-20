"""Test module for pyproject.toml based project."""


class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def subtract(self, a: int, b: int) -> int:
        """Subtract two numbers."""
        return a - b


def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


VERSION = "2.1.0"
