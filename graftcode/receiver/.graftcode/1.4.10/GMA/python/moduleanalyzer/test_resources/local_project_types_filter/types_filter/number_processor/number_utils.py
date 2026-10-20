"""
Number utilities class - Python equivalent of NumberUtils.cs
"""

import math


class NumberUtils:
    """Utility class for number processing operations."""

    def sum_of_digits(self, number: int) -> int:
        """
        Calculate the sum of digits in a number.

        Args:
            number: The number to process

        Returns:
            Sum of all digits in the number
        """
        sum_digits = 0
        number = abs(number)
        while number > 0:
            sum_digits += number % 10
            number //= 10
        return sum_digits

    def is_even(self, number: int) -> bool:
        """
        Check if a number is even.

        Args:
            number: The number to check

        Returns:
            True if number is even, False otherwise
        """
        return number % 2 == 0

    def factorial(self, n: int) -> int:
        """
        Calculate the factorial of a number.

        Args:
            n: The number to calculate factorial for

        Returns:
            Factorial of n

        Raises:
            ValueError: If n is negative
        """
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1

        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    def absolute_difference(self, a: int, b: int) -> int:
        """
        Calculate the absolute difference between two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Absolute difference |a - b|
        """
        return abs(a - b)
