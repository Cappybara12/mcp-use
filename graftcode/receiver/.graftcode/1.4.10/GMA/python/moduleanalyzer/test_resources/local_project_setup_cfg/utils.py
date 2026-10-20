"""Test module for setup.cfg based project."""


class StringUtils:
    """Utility class for string operations."""

    @staticmethod
    def reverse(text: str) -> str:
        """Reverse a string."""
        return text[::-1]

    @staticmethod
    def uppercase(text: str) -> str:
        """Convert string to uppercase."""
        return text.upper()


def concat(a: str, b: str) -> str:
    """Concatenate two strings."""
    return a + b


DEFAULT_SEPARATOR = ", "
