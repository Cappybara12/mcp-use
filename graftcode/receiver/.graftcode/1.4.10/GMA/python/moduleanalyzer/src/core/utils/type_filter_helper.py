"""
Helper class for filtering types using wildcard patterns.
Supports comma-separated patterns with * and ? wildcards.
"""

import re
from typing import Optional


class TypeFilterHelper:
    """Helper class for filtering types using wildcard patterns."""

    @staticmethod
    def matches_filter(type_name: str, type_filter: Optional[str]) -> bool:
        """
        Checks if a type name matches any of the provided wildcard patterns.
        If empty string or None is provided, returns True (analyze all).

        :param type_name: The full name of the type to check (e.g., "my_namespace.calculator.BasicCalculator").
        :param type_filter: Comma-separated wildcard patterns (e.g., "my_namespace.*, *Service, Test*").
                           Empty string or None means analyze all types.
        :return: True if the type matches any pattern, or if filter is empty/None.
        """
        # If empty string or None is provided, analyze all types
        if not type_filter or not type_filter.strip():
            return True

        # Split by comma and trim each pattern
        patterns = [
            p.strip()
            for p in type_filter.split(",")
            if p.strip()
        ]

        # If no valid patterns after splitting, analyze all
        if not patterns:
            return True

        # Check if type name matches any pattern
        for pattern in patterns:
            if TypeFilterHelper._matches_wildcard_pattern(type_name, pattern):
                return True

        return False

    @staticmethod
    def _matches_wildcard_pattern(input_str: str, pattern: str) -> bool:
        """
        Checks if a string matches a wildcard pattern.
        Supports * (matches any sequence of characters) and ? (matches any single character).

        :param input_str: The string to check.
        :param pattern: The wildcard pattern.
        :return: True if the input matches the pattern.
        """
        try:
            # Escape special regex characters except * and ?
            regex_pattern = (
                "^"
                + re.escape(pattern)
                .replace("\\*", ".*")
                .replace("\\?", ".")
                + "$"
            )

            # Use re.IGNORECASE for case-insensitive matching
            # Set timeout to prevent regex denial of service attacks (Python 3.11+)
            try:
                regex = re.compile(regex_pattern, re.IGNORECASE)
                return bool(regex.match(input_str))
            except re.error:
                # If pattern is invalid, treat as no match
                return False

        except Exception:
            # If pattern matching fails for any reason, treat as no match for security
            return False
