import inspect
from typing import Any, Dict, List, Optional
import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_global_method_analyzer_handler import (
    GetGlobalMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers


# Real test functions for analysis
def simple_test_function() -> str:
    """Simple function with no parameters."""
    return "test_result"


def function_with_params(a: int, b: str, c: float = 3.14) -> Dict[str, Any]:
    """Function with multiple parameters including default."""
    return {"a": a, "b": b, "c": c}


def function_with_complex_signature(
    required: str, optional: Optional[int] = None, *args: str, **kwargs: Any
) -> List[Any]:
    """Function with complex parameter signature."""
    return [required, optional, args, kwargs]


async def async_test_function(delay: float = 1.0) -> str:
    """Async function for testing."""
    import asyncio

    await asyncio.sleep(delay)
    return "async_complete"


class TestGetGlobalMethodAnalyzerHandlerReal(unittest.TestCase):
    """Real-case test cases for GetGlobalMethodAnalyzerHandler."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers."""
        self.handler = GetGlobalMethodAnalyzerHandler()
        self.handlers = Handlers()
        self.parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

    def test_analyze_simple_function(self) -> None:
        """Test analysis of a simple real function."""
        # Prepare function with params attribute (as module analyzer would)
        test_func = simple_test_function
        test_func.params = []  # No parameters

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Verify the function name is in the payload
        self.assertTrue(len(result.payload) > 0)
        # The first payload item should be the method name
        self.assertEqual(result.payload[0], "simple_test_function")

    def test_analyze_function_with_parameters(self) -> None:
        """Test analysis of function with parameters."""
        test_func = function_with_params
        # Extract real parameter names from function signature
        sig = inspect.signature(test_func)
        test_func.params = list(sig.parameters.keys())

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)

        # Verify parameters were processed (payload length > basic method info)
        self.assertTrue(
            len(result.payload) >= 4
        )  # name + return_type + modifiers + parameters

        # Function name should be first
        self.assertEqual(result.payload[0], "function_with_params")

    def test_analyze_function_with_complex_signature(self) -> None:
        """Test analysis of function with complex parameter signature."""
        test_func = function_with_complex_signature
        sig = inspect.signature(test_func)
        test_func.params = list(sig.parameters.keys())

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Verify basic structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)

        # Should have processed complex parameters
        self.assertTrue(len(result.payload) >= 4)
        self.assertEqual(result.payload[0], "function_with_complex_signature")

    def test_analyze_async_function(self) -> None:
        """Test analysis of async function."""
        test_func = async_test_function
        sig = inspect.signature(test_func)
        test_func.params = list(sig.parameters.keys())

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Verify structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.payload[0], "async_test_function")

    def test_function_without_params_attribute(self) -> None:
        """Test function that doesn't have params attribute (no parameters to process)."""
        test_func = simple_test_function
        # Don't add params attribute

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Should still work, just without parameter processing
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.payload[0], "simple_test_function")

    def test_function_with_empty_params(self) -> None:
        """Test function with empty params list."""
        test_func = simple_test_function
        test_func.params = []  # Empty but present

        result = self.handler.generate_unified_graft_model(
            test_func, self.parent_command, self.handlers
        )

        # Should process without parameters
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)

    def test_function_with_type_annotations(self) -> None:
        """Test function with type annotations."""

        def typed_function(x: int, y: str = "default") -> bool:
            """Function with type annotations."""
            return True

        # Set up like module analyzer would
        sig = inspect.signature(typed_function)
        typed_function.params = list(sig.parameters.keys())

        result = self.handler.generate_unified_graft_model(
            typed_function, self.parent_command, self.handlers
        )

        # Verify processing
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.payload[0], "typed_function")

    def test_lambda_function_analysis(self) -> None:
        """Test analysis of lambda-like function."""

        def lambda_like_function(x, y):
            """Function that simulates lambda behavior."""
            return x + y

        lambda_like_function.params = ["x", "y"]

        result = self.handler.generate_unified_graft_model(
            lambda_like_function, self.parent_command, self.handlers
        )

        # Verify processing
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.payload[0], "lambda_like_function")

    def test_method_name_extraction(self) -> None:
        """Test various ways method names can be extracted."""
        # Test with __name__ attribute
        func1 = function_with_params
        self.assertEqual(
            self.handler.add_method_name_to_payload(
                UnifiedGraftModel(
                    RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
                ),
                func1,
            ).payload[0],
            "function_with_params",
        )

        # Test with name attribute fallback (when __name__ is not available)
        class RealFunctionLikeObject:
            """Object that simulates a function with name attribute but no __name__."""

            name = "custom_function_name"

            def __call__(self):
                return "test"

        function_like_obj = RealFunctionLikeObject()
        result = self.handler.add_method_name_to_payload(
            UnifiedGraftModel(
                RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
            ),
            function_like_obj,
        )
        self.assertEqual(result.payload[0], "custom_function_name")

    def test_return_type_extraction(self) -> None:
        """Test return type extraction from real functions."""

        # Function with return annotation
        def annotated_function() -> str:
            return "test"

        base_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        result = self.handler.add_return_type_to_payload(
            base_command, annotated_function, self.handlers
        )

        # Should have added return type information
        self.assertTrue(len(result.payload) > 0)
        # The added item should be a UnifiedGraftModel for TYPE_USAGE
        added_item = result.payload[0]
        self.assertIsInstance(added_item, UnifiedGraftModel)

    def test_integration_with_real_module_data(self) -> None:
        """Test integration with real function from test resources."""
        # Use a real function from our test resources
        from moduleanalyzer.test_resources.test_classes import sample_global_function

        # Set up params as the module analyzer would
        sig = inspect.signature(sample_global_function)
        sample_global_function.params = list(sig.parameters.keys())

        result = self.handler.generate_unified_graft_model(
            sample_global_function, self.parent_command, self.handlers
        )

        # Should handle real function object
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)
        self.assertEqual(result.payload[0], "sample_global_function")


if __name__ == "__main__":
    unittest.main()
