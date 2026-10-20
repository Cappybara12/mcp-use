"""
Advanced math operations class - Python equivalent of AdvancedMath.cs
"""

import math


class AdvancedMath:
    """Class for advanced mathematical operations."""

    def power(self, base_value: float, exponent: float) -> float:
        """
        Calculate base raised to the power of exponent.

        Args:
            base_value: The base value
            exponent: The exponent value

        Returns:
            Result of base_value raised to exponent
        """
        return math.pow(base_value, exponent)

    def square_root(self, value: float) -> float:
        """
        Calculate the square root of a value.

        Args:
            value: The value to calculate square root for

        Returns:
            Square root of value

        Raises:
            ValueError: If value is negative
        """
        if value < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return math.sqrt(value)

    def modulo(self, dividend: int, divisor: int) -> int:
        """
        Calculate the modulo (remainder) of division.

        Args:
            dividend: The dividend
            divisor: The divisor

        Returns:
            Remainder of dividend divided by divisor
        """
        return dividend % divisor

    def average(self, numbers: list[float]) -> float:
        """
        Calculate the average of an array of numbers.

        Args:
            numbers: List of numbers

        Returns:
            Average value

        Raises:
            ValueError: If numbers is None or empty
        """
        if numbers is None or len(numbers) == 0:
            raise ValueError("Array cannot be None or empty")
        return sum(numbers) / len(numbers)
