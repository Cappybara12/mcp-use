"""
Integration tests for method filtering in PythonModuleAnalyzerLocal.
"""

from typing import Dict, List, Set

import pytest

from graftcode_protocol.protocol.deserializers.unified_graft_model_deserializer import (
    UnifiedGraftModelDeserializer,
)
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.module_analyzer_local import (
    PythonModuleAnalyzerLocal,
)


def extract_instance_methods_by_type(
    decoded_result: UnifiedGraftModel,
) -> Dict[str, Set[str]]:
    methods_by_type: Dict[str, Set[str]] = {}

    if decoded_result is None or decoded_result.payload is None:
        return methods_by_type

    for payload_item in decoded_result.payload:
        if (
            not isinstance(payload_item, UnifiedGraftModel)
            or payload_item.graft_model_type != UnifiedGraftModelType.TYPE_DEF
            or payload_item.payload is None
            or len(payload_item.payload) < 2
        ):
            continue

        namespace_name = str(payload_item.payload[0] or "")
        class_name = str(payload_item.payload[1] or "")
        if not namespace_name or not class_name:
            continue

        full_name = f"{namespace_name}.{class_name}"
        method_names: Set[str] = set()

        for member in payload_item.payload[5:]:
            if not isinstance(member, UnifiedGraftModel) or member.payload is None:
                continue
            if member.graft_model_type.value in (
                UnifiedGraftModelType.INSTANCE_METHOD.value,
                UnifiedGraftModelType.STATIC_METHOD.value,
            ) and len(member.payload) >= 1:
                method_names.add(str(member.payload[0]))

        methods_by_type[full_name] = method_names

    return methods_by_type


def find_type_key(methods_by_type: Dict[str, Set[str]], class_suffix: str) -> str:
    for key in methods_by_type:
        if key.endswith(class_suffix):
            return key
    raise AssertionError(f"No type ending with {class_suffix!r} in {list(methods_by_type)}")


class TestMethodFilter:
    @pytest.fixture
    def analyzer(self):
        return PythonModuleAnalyzerLocal()

    @pytest.fixture
    def types_filter_path(self):
        return "moduleanalyzer/test_resources/local_project_types_filter"

    def test_method_filter_empty_includes_all_calculator_methods(
        self, analyzer, types_filter_path
    ):
        result = analyzer.analyze_local(types_filter_path, "*Calculator", "")
        decoded = UnifiedGraftModelDeserializer(list(result), len(result)).deserialize()

        methods_by_type = extract_instance_methods_by_type(decoded)
        calculator_key = find_type_key(methods_by_type, "BasicCalculator")

        assert methods_by_type[calculator_key] == {"add", "subtract", "multiply", "divide"}

    def test_method_filter_bare_name_matches_method_on_included_types(
        self, analyzer, types_filter_path
    ):
        result = analyzer.analyze_local(types_filter_path, "", "add")
        decoded = UnifiedGraftModelDeserializer(list(result), len(result)).deserialize()

        methods_by_type = extract_instance_methods_by_type(decoded)
        calculator_key = find_type_key(methods_by_type, "BasicCalculator")

        assert methods_by_type[calculator_key] == {"add"}

    def test_method_filter_wildcard_prefix(self, analyzer, types_filter_path):
        result = analyzer.analyze_local(types_filter_path, "*Calculator", "add*")
        decoded = UnifiedGraftModelDeserializer(list(result), len(result)).deserialize()

        methods_by_type = extract_instance_methods_by_type(decoded)
        assert len(methods_by_type) == 1
        calculator_key = find_type_key(methods_by_type, "BasicCalculator")
        assert methods_by_type[calculator_key] == {"add"}

    def test_method_filter_with_type_filter_applies_both(
        self, analyzer, types_filter_path
    ):
        result = analyzer.analyze_local(types_filter_path, "*Calculator", "add,subtract")
        decoded = UnifiedGraftModelDeserializer(list(result), len(result)).deserialize()

        methods_by_type = extract_instance_methods_by_type(decoded)
        assert len(methods_by_type) == 1
        calculator_key = find_type_key(methods_by_type, "BasicCalculator")
        assert methods_by_type[calculator_key] == {"add", "subtract"}

    def test_method_filter_no_match_leaves_type_without_methods(
        self, analyzer, types_filter_path
    ):
        result = analyzer.analyze_local(
            types_filter_path, "*Calculator", "nonexistent_method*"
        )
        decoded = UnifiedGraftModelDeserializer(list(result), len(result)).deserialize()

        methods_by_type = extract_instance_methods_by_type(decoded)
        calculator_key = find_type_key(methods_by_type, "BasicCalculator")
        assert methods_by_type[calculator_key] == set()

    def test_get_hosted_library_statistics_local_respects_method_filter(
        self, analyzer, types_filter_path
    ):
        all_methods_json = analyzer.get_hosted_library_statistics_local(
            analyzer.analyze_local(types_filter_path, "*Calculator", "")
        )
        filtered_json = analyzer.get_hosted_library_statistics_local(
            analyzer.analyze_local(types_filter_path, "*Calculator", "multiply")
        )

        assert '"MethodsExposed": 4' in all_methods_json or '"MethodsExposed":4' in all_methods_json
        assert '"MethodsExposed": 1' in filtered_json or '"MethodsExposed":1' in filtered_json
