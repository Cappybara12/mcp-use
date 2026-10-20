import inspect
from typing import List, Optional

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
import pytest

from moduleanalyzer.src.core.handler.get_global_method_analyzer_handler import (
    GetGlobalMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers


class TestGetGlobalMethodAnalyzerHandler:
    """Test cases for GetGlobalMethodAnalyzerHandler using real implementations."""

    @pytest.fixture
    def handler(self):
        """Create a real GetGlobalMethodAnalyzerHandler instance."""
        return GetGlobalMethodAnalyzerHandler()

    @pytest.fixture
    def real_handlers(self):
        """Create real Handlers instance with all real handler implementations."""
        return Handlers()

    @pytest.fixture
    def parent_command(self):
        """Create a real parent command for testing."""
        return UnifiedGraftModel(RuntimeName.Python, UnifiedGraftModelType.LIBRARY, [])

    def test_generate_unified_graft_model_with_simple_function(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with a simple function."""

        def simple_function():
            """A simple function with no parameters."""
            return "hello"

        # Execute
        result = handler.generate_unified_graft_model(
            simple_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        assert result.runtime_name == RuntimeName.Python
        # Should have method name, return type, and modifiers in payload
        assert len(result.payload) >= 3

    def test_generate_unified_graft_model_with_typed_function(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with a function that has type hints."""

        def typed_function(name: str, age: int) -> str:
            """A function with type hints."""
            return f"Hello {name}, you are {age} years old"

        # Execute
        result = handler.generate_unified_graft_model(
            typed_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        assert result.runtime_name == RuntimeName.Python
        # Should have method name, return type, and modifiers (parameters only added if params attribute exists)
        assert len(result.payload) >= 3

    def test_generate_unified_graft_model_with_optional_parameters(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with optional parameters."""

        def function_with_defaults(
            required_param: str, optional_param: int = 42
        ) -> bool:
            """Function with required and optional parameters."""
            return len(required_param) > optional_param

        # Execute
        result = handler.generate_unified_graft_model(
            function_with_defaults, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should have basic components (parameters only added if params attribute exists)
        assert len(result.payload) >= 3

    def test_generate_unified_graft_model_with_complex_types(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with complex type annotations."""

        def complex_function(
            items: List[str], count: Optional[int] = None
        ) -> List[int]:
            """Function with complex type annotations."""
            if count is None:
                count = len(items)
            return [len(item) for item in items[:count]]

        # Execute
        result = handler.generate_unified_graft_model(
            complex_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should handle complex types properly
        assert len(result.payload) >= 3

    def test_generate_unified_graft_model_with_no_return_annotation(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with function that has no return annotation."""

        def no_return_annotation(x, y):
            """Function without type hints."""
            return x + y

        # Execute
        result = handler.generate_unified_graft_model(
            no_return_annotation, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should still work without type annotations
        assert len(result.payload) >= 3

    def test_generate_unified_graft_model_with_custom_attributes(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with function that has custom attributes."""

        def custom_function(data: str) -> str:
            """Function that will have custom attributes added."""
            return data.upper()

        # Add custom attributes that the handler looks for
        custom_function.params = ["data"]
        custom_function.return_type = "str"
        custom_function.modifiers = ["public"]

        # Execute
        result = handler.generate_unified_graft_model(
            custom_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should include parameters since params attribute is present and non-empty
        assert len(result.payload) >= 4

    def test_generate_unified_graft_model_with_empty_params_attribute(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with function that has empty params attribute."""

        def empty_params_function() -> None:
            """Function with empty params attribute."""
            pass

        # Add empty params attribute
        empty_params_function.params = []

        # Execute
        result = handler.generate_unified_graft_model(
            empty_params_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should not include parameters section for empty params; docstring adds COMMENT_DOC
        assert len(result.payload) == 4  # name, return type, modifiers, COMMENT_DOC
        assert not any(
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
            for item in result.payload
        )
        assert any(
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.COMMENT_DOC
            for item in result.payload
        )

    def test_generate_unified_graft_model_with_non_list_params(
        self, handler, real_handlers, parent_command
    ):
        """Test generate_unified_graft_model with function that has invalid params attribute."""

        def invalid_params_function(x: int) -> int:
            """Function with invalid params attribute."""
            return x * 2

        # Add invalid params attribute (not a list)
        invalid_params_function.params = "invalid"

        # Execute
        result = handler.generate_unified_graft_model(
            invalid_params_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should not include parameters section for invalid params; docstring adds COMMENT_DOC
        assert len(result.payload) == 4  # name, return type, modifiers, COMMENT_DOC
        assert not any(
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
            for item in result.payload
        )
        assert any(
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.COMMENT_DOC
            for item in result.payload
        )

    def test_add_method_name_to_payload_with_real_function(self, handler):
        """Test add_method_name_to_payload with a real function."""

        def test_function():
            """Test function for name extraction."""
            pass

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        # Execute
        result = handler.add_method_name_to_payload(command, test_function)

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert len(result.payload) == 1
        assert result.payload[0] == "test_function"

    def test_add_return_type_to_payload_with_annotation(self, handler, real_handlers):
        """Test add_return_type_to_payload with function that has return annotation."""

        def annotated_function() -> str:
            """Function with return type annotation."""
            return "test"

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        # Execute
        result = handler.add_return_type_to_payload(
            command, annotated_function, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert len(result.payload) == 1
        # Should have added a UnifiedGraftModel for the return type
        assert isinstance(result.payload[0], UnifiedGraftModel)

    def test_add_return_type_to_payload_without_annotation(
        self, handler, real_handlers
    ):
        """Test add_return_type_to_payload with function without return annotation."""

        def no_annotation_function():
            """Function without return type annotation."""
            return 42

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        # Execute
        result = handler.add_return_type_to_payload(
            command, no_annotation_function, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert len(result.payload) == 1
        # Should have added a UnifiedGraftModel for the default return type
        assert isinstance(result.payload[0], UnifiedGraftModel)

    def test_add_modifiers_to_payload_with_real_function(self, handler, real_handlers):
        """Test add_modifiers_to_payload with a real function."""

        def regular_function():
            """Regular function for modifier testing."""
            pass

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        # Execute
        result = handler.add_modifiers_to_payload(
            command, regular_function, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert len(result.payload) == 1
        # Should have added the modifier information (could be UnifiedGraftModel or other type)
        assert result.payload[0] is not None

    def test_add_parameters_to_payload_with_real_function(self, handler, real_handlers):
        """Test add_parameters_to_payload with a real function."""

        def function_with_params(param1: str, param2: int = 10):
            """Function with parameters for testing."""
            return f"{param1}: {param2}"

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        # Execute
        result = handler.add_parameters_to_payload(
            command, function_with_params, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert len(result.payload) == 1
        # Should have added a UnifiedGraftModel for the parameters
        assert isinstance(result.payload[0], UnifiedGraftModel)

    def test_real_world_function_analysis(self, handler, real_handlers, parent_command):
        """Test with a real-world like function."""

        def calculate_statistics(
            data: List[float], include_median: bool = True
        ) -> dict:
            """
            Calculate basic statistics for a list of numbers.

            Args:
                data: List of numbers to analyze
                include_median: Whether to include median in results

            Returns:
                Dictionary containing statistical measures
            """
            if not data:
                return {}

            stats = {
                "mean": sum(data) / len(data),
                "min": min(data),
                "max": max(data),
                "count": len(data),
            }

            if include_median:
                sorted_data = sorted(data)
                n = len(sorted_data)
                if n % 2 == 0:
                    stats["median"] = (
                        sorted_data[n // 2 - 1] + sorted_data[n // 2]
                    ) / 2
                else:
                    stats["median"] = sorted_data[n // 2]

            return stats

        # Execute
        result = handler.generate_unified_graft_model(
            calculate_statistics, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        assert result.runtime_name == RuntimeName.Python
        # Should have basic components (parameters only added if params attribute exists)
        assert len(result.payload) >= 3

    def test_lambda_function_analysis(self, handler, real_handlers, parent_command):
        """Test with a lambda function."""

        def lambda_func(x, y):
            return x + y

        # Execute
        result = handler.generate_unified_graft_model(
            lambda_func, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Lambda functions should still be analyzed properly
        assert len(result.payload) >= 3

    def test_builtin_function_analysis(self, handler, real_handlers, parent_command):
        """Test with a built-in function."""

        # Execute with built-in len function
        result = handler.generate_unified_graft_model(
            len, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Built-in functions should be handled gracefully
        assert len(result.payload) >= 3

    def test_function_with_inspect_signature(
        self, handler, real_handlers, parent_command
    ):
        """Test that the handler works with inspect.signature information."""

        def inspectable_function(a: int, b: str = "default", *args, **kwargs) -> tuple:
            """Function that can be inspected with inspect module."""
            return (a, b, args, kwargs)

        # Verify we can inspect this function
        sig = inspect.signature(inspectable_function)
        assert len(sig.parameters) == 4  # a, b, args, kwargs

        # Execute
        result = handler.generate_unified_graft_model(
            inspectable_function, parent_command, real_handlers
        )

        # Verify
        assert isinstance(result, UnifiedGraftModel)
        assert result.graft_model_type == UnifiedGraftModelType.GLOBAL_METHOD
        # Should handle complex signatures properly
        assert len(result.payload) >= 3
