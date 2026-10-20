"""
Arithmetic utilities class - Python equivalent of ArithmeticUtils.cs
"""


class ArithmeticUtils:
    """Utility class for arithmetic operations."""

    def sum(self, numbers: list[int]) -> int:
        """
        Calculate the sum of an array of integers.

        Args:
            numbers: List of integers to sum

        Returns:
            Sum of all numbers

        Raises:
            ValueError: If numbers is None
        """
        if numbers is None:
            raise ValueError("numbers cannot be None")
        return sum(numbers)

    def maximum(self, a: int, b: int, c: int) -> int:
        """
        Find the maximum of three integers.

        Args:
            a: First integer
            b: Second integer
            c: Third integer

        Returns:
            Maximum value among a, b, and c
        """
        return max(a, max(b, c))

    def minimum(self, a: int, b: int, c: int) -> int:
        """
        Find the minimum of three integers.

        Args:
            a: First integer
            b: Second integer
            c: Third integer

        Returns:
            Minimum value among a, b, and c
        """
        return min(a, min(b, c))

    def percentage(self, part: float, whole: float) -> float:
        """
        Calculate percentage: (part / whole) * 100.

        Args:
            part: The part value
            whole: The whole value

        Returns:
            Percentage value

        Raises:
            ZeroDivisionError: If whole is zero
        """
        if whole == 0:
            raise ZeroDivisionError("Whole value cannot be zero")
        return (part / whole) * 100
