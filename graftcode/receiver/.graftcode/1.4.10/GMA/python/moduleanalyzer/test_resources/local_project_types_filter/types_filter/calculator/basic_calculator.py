"""
Basic calculator class - Python equivalent of BasicCalculator.cs
"""


class BasicCalculator:
    """Basic calculator with fundamental arithmetic operations."""

    def add(self, a: int, b: int) -> int:
        """
        Add two integers.

        Args:
            a: First integer
            b: Second integer

        Returns:
            Sum of a and b
        """
        return a + b

    def subtract(self, a: int, b: int) -> int:
        """
        Subtract b from a.

        Args:
            a: First integer (minuend)
            b: Second integer (subtrahend)

        Returns:
            Difference of a and b
        """
        return a - b

    def multiply(self, a: int, b: int) -> int:
        """
        Multiply two integers.

        Args:
            a: First integer
            b: Second integer

        Returns:
            Product of a and b
        """
        return a * b

    def divide(self, a: float, b: float) -> float:
        """
        Divide a by b.

        Args:
            a: Dividend
            b: Divisor

        Returns:
            Quotient of a and b

        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b
