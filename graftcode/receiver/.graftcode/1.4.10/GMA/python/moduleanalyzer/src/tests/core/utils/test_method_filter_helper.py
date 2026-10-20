"""Unit tests for MethodFilterHelper."""

import pytest

from moduleanalyzer.src.core.utils.method_filter_helper import MethodFilterHelper


class TestMethodFilterHelper:
    @pytest.mark.parametrize(
        "method_name,method_filter,expected",
        [
            ("get_value", "get*", True),
            ("set_value", "get*", False),
            ("get_value", "", True),
            ("get_value", None, True),
            ("get_value", "   ", True),
        ],
    )
    def test_matches_filter_wildcard_and_empty(
        self, method_name, method_filter, expected
    ):
        assert (
            MethodFilterHelper.matches_filter(
                method_name, method_filter, "my_namespace.my_type"
            )
            is expected
        )

    @pytest.mark.parametrize(
        "method_name,method_filter,expected",
        [
            (
                "multiply",
                "types_filter.calculator.basic_calculator.BasicCalculator.multiply",
                True,
            ),
            ("multiply", "OtherType.multiply", False),
            ("add", "*.BasicCalculator.add", True),
        ],
    )
    def test_matches_filter_qualified_patterns(
        self, method_name, method_filter, expected
    ):
        assert (
            MethodFilterHelper.matches_filter(
                method_name,
                method_filter,
                "types_filter.calculator.basic_calculator.BasicCalculator",
            )
            is expected
        )

    @pytest.mark.parametrize(
        "method_name,method_filter,expected",
        [
            ("add", "add,subtract", True),
            ("multiply", "add,subtract", False),
            ("add", " add , subtract ", True),
        ],
    )
    def test_matches_filter_multiple_patterns(
        self, method_name, method_filter, expected
    ):
        assert (
            MethodFilterHelper.matches_filter(
                method_name, method_filter, "types_filter.calculator"
            )
            is expected
        )
