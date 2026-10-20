"""
Tests for type filtering functionality in PythonModuleAnalyzerLocal.
Similar to TypeFilter tests in .NET ModuleAnalyzer.
"""

from typing import List

import pytest

from graftcode_protocol.protocol.deserializers.unified_graft_model_deserializer import (
    UnifiedGraftModelDeserializer,
)
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.module_analyzer_local import (
    PythonModuleAnalyzerLocal,
)


def extract_type_names(decoded_result: UnifiedGraftModel) -> List[str]:
    """
    Extracts all full type names (module.className) from the decoded result.
    TYPE_DEF structure: [namespace, className, moduleFullName, moduleHash, modifier, ...]

    :param decoded_result: The deserialized UnifiedGraftModel result
    :return: List of full type names in format "namespace.className"
    """
    type_names: List[str] = []

    if decoded_result is None or decoded_result.payload is None:
        return type_names

    for payload_item in decoded_result.payload:
        if (
            isinstance(payload_item, UnifiedGraftModel)
            and payload_item.graft_model_type == UnifiedGraftModelType.TYPE_DEF
        ):
            if payload_item.payload is None or len(payload_item.payload) < 2:
                continue

            # TYPE_DEF structure: [namespace, className, moduleFullName, moduleHash, modifier, ...]
            namespace_name = (
                str(payload_item.payload[0]) if payload_item.payload[0] else ""
            )
            class_name = (
                str(payload_item.payload[1]) if payload_item.payload[1] else ""
            )

            if namespace_name and class_name:
                # Combine namespace and className to get full type name
                type_names.append(f"{namespace_name}.{class_name}")

    return type_names


class TestTypeFilter:
    """Tests for type filtering functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create a PythonModuleAnalyzerLocal instance."""
        return PythonModuleAnalyzerLocal()

    @pytest.fixture
    def types_filter_path(self):
        """Get the path to the local_project_types_filter test resource."""
        # Path relative to project root, similar to other tests
        return "moduleanalyzer/test_resources/local_project_types_filter"

    def test_type_filter_empty_string_analyzes_all_types(
        self, analyzer, types_filter_path
    ):
        """Tests that empty string filter analyzes all types."""
        result = analyzer.analyze_local(types_filter_path, "")

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        # Should contain all 4 types
        assert len(type_names) == 4
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "math_operations.advanced_math.AdvancedMath" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names

    def test_type_filter_no_parameter_analyzes_all_types(
        self, analyzer, types_filter_path
    ):
        """Tests that no filter parameter (default empty string) analyzes all types."""
        result = analyzer.analyze_local(types_filter_path)

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        # Should contain all 4 types
        assert len(type_names) == 4
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "math_operations.advanced_math.AdvancedMath" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names

    def test_type_filter_namespace_wildcard_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering by namespace wildcard pattern."""
        # Filter: calculator.* should match only BasicCalculator
        result = analyzer.analyze_local(
            types_filter_path, "calculator.*"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 1
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" not in type_names
        assert "math_operations.advanced_math.AdvancedMath" not in type_names
        assert "number_processor.number_utils.NumberUtils" not in type_names

    def test_type_filter_class_name_wildcard_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering by class name wildcard pattern."""
        # Filter: *Utils should match ArithmeticUtils and NumberUtils
        result = analyzer.analyze_local(types_filter_path, "*Utils")

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 2
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names
        assert "calculator.basic_calculator.BasicCalculator" not in type_names
        assert "math_operations.advanced_math.AdvancedMath" not in type_names

    def test_type_filter_multiple_patterns_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with multiple comma-separated patterns."""
        # Filter: calculator.*, *Utils should match BasicCalculator, ArithmeticUtils, and NumberUtils
        result = analyzer.analyze_local(
            types_filter_path, "calculator.*, *Utils"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 3
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names
        assert "math_operations.advanced_math.AdvancedMath" not in type_names

    def test_type_filter_full_namespace_wildcard_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with full namespace wildcard."""
        # Filter: *.* should match all types (any namespace, any module)
        result = analyzer.analyze_local(types_filter_path, "*.*")

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 4
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "math_operations.advanced_math.AdvancedMath" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names

    def test_type_filter_no_match_returns_empty_result(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with pattern that matches nothing."""
        # Filter: NonExistentNamespace.* should match nothing
        result = analyzer.analyze_local(
            types_filter_path, "NonExistentNamespace.*"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 0

    def test_type_filter_specific_full_type_name_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with specific full type name."""
        # Filter: Exact full type name should match only that type
        result = analyzer.analyze_local(
            types_filter_path, "math_operations.advanced_math.AdvancedMath"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 1
        assert "math_operations.advanced_math.AdvancedMath" in type_names

    def test_type_filter_question_mark_wildcard_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with question mark wildcard pattern."""
        # Filter: BasicCalculat?r should match BasicCalculator (single character wildcard)
        result = analyzer.analyze_local(
            types_filter_path, "calculator.*.BasicCalculat?r"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 1
        assert "calculator.basic_calculator.BasicCalculator" in type_names

    def test_type_filter_starts_with_wildcard_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with pattern starting with wildcard."""
        # Filter: *Calculator should match BasicCalculator
        result = analyzer.analyze_local(types_filter_path, "*Calculator")

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 1
        assert "calculator.basic_calculator.BasicCalculator" in type_names

    def test_type_filter_wildcard_in_middle_filters_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests filtering with pattern containing wildcard in the middle."""
        # Filter: *helper.* should match arithmetic_helper.ArithmeticUtils
        result = analyzer.analyze_local(
            types_filter_path, "*helper.*"
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 1
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names

    def test_type_filter_whitespace_in_patterns_handled_correctly(
        self, analyzer, types_filter_path
    ):
        """Tests that whitespace in filter patterns is handled correctly."""
        # Filter with whitespace should be trimmed and work correctly
        result = analyzer.analyze_local(
            types_filter_path, " calculator.* , *Utils "
        )

        deserializer = UnifiedGraftModelDeserializer(list(result), len(result))
        decoded_result = deserializer.deserialize()

        type_names = extract_type_names(decoded_result)

        assert len(type_names) == 3
        assert "calculator.basic_calculator.BasicCalculator" in type_names
        assert "arithmetic_helper.arithmetic_utils.ArithmeticUtils" in type_names
        assert "number_processor.number_utils.NumberUtils" in type_names
