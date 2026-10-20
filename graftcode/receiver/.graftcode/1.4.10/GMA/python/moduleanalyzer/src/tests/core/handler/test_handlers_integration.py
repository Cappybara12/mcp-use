"""
Integration tests for Handlers class.

Tests the complete integration of the Handlers registry with real Python objects,
verifying that all handlers work together correctly in realistic scenarios.
"""

from pathlib import Path
import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_global_field_analyzer_handler import (
    GetGlobalFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_global_method_analyzer_handler import (
    GetGlobalMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.interface_analyzer import InterfaceAnalyzer


class TestHandlersIntegration(unittest.TestCase):
    """Integration test cases for Handlers class with real implementations."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handlers = Handlers()

        # Get path to test resources
        self.test_resources_dir = Path(__file__).parent.parent.parent / "resources"
        self.simple_module_path = self.test_resources_dir / "simple_module.py"

    def test_all_handlers_are_registered(self) -> None:
        """Test that all required handlers are properly registered."""
        # Test analyzer handlers
        expected_analyzer_handlers = {
            UnifiedGraftModelType.TYPE_DEF,
            UnifiedGraftModelType.INSTANCE_METHOD,
            UnifiedGraftModelType.ABSTRACT_INSTANCE_METHOD,
            UnifiedGraftModelType.STATIC_METHOD,
            UnifiedGraftModelType.ABSTRACT_STATIC_METHOD,
            UnifiedGraftModelType.STATIC_FIELD,
            UnifiedGraftModelType.CONSTRUCTOR,
            UnifiedGraftModelType.INSTANCE_FIELD,
            UnifiedGraftModelType.PROPERTY,
            UnifiedGraftModelType.GLOBAL_METHOD,
            UnifiedGraftModelType.GLOBAL_FIELD,
        }

        for handler_type in expected_analyzer_handlers:
            self.assertIn(
                handler_type,
                self.handlers.analyzer_handler,
                f"Missing analyzer handler for {handler_type}",
            )
            self.assertIsNotNone(
                self.handlers.analyzer_handler[handler_type],
                f"Handler for {handler_type} is None",
            )

        # Test shared handlers
        expected_shared_handlers = {
            UnifiedGraftModelType.ARGUMENT_NAME,
            UnifiedGraftModelType.CLASS_NAME,
            UnifiedGraftModelType.METHOD_NAME,
            UnifiedGraftModelType.MODIFIER,
            UnifiedGraftModelType.TYPE_USAGE,
            UnifiedGraftModelType.PARAMETERS_ARRAY,
            UnifiedGraftModelType.NAMESPACE,
            UnifiedGraftModelType.MODULE_FULL_NAME,
            UnifiedGraftModelType.MODULE_HASH,
            UnifiedGraftModelType.FIELD_NAME,
        }

        for handler_type in expected_shared_handlers:
            self.assertIn(
                handler_type,
                self.handlers.shared_handler,
                f"Missing shared handler for {handler_type}",
            )
            self.assertIsNotNone(
                self.handlers.shared_handler[handler_type],
                f"Shared handler for {handler_type} is None",
            )

    def test_global_method_handler_with_real_function(self) -> None:
        """Test that GLOBAL_METHOD handler works with real functions."""

        # Create a real function
        def test_function(param: str) -> str:
            return f"processed: {param}"

        test_function.params = ["param"]

        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Use the registered handler
        handler = self.handlers.analyzer_handler[UnifiedGraftModelType.GLOBAL_METHOD]
        self.assertIsInstance(handler, GetGlobalMethodAnalyzerHandler)

        result = handler.generate_unified_graft_model(
            test_function, parent_command, self.handlers
        )

        # Verify result
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_METHOD)

    def test_global_field_handler_with_real_data(self) -> None:
        """Test that GLOBAL_FIELD handler works with real variable data."""
        # Simulate real variable data
        variable_data = {"name": "TEST_CONSTANT", "type": str, "value": "test_value"}

        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Use the registered handler
        handler = self.handlers.analyzer_handler[UnifiedGraftModelType.GLOBAL_FIELD]
        self.assertIsInstance(handler, GetGlobalFieldAnalyzerHandler)

        result = handler.generate_unified_graft_model(
            variable_data, parent_command, self.handlers
        )

        # Verify result
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)

    def test_type_def_handler_with_real_class(self) -> None:
        """Test TYPE_DEF handler with a real Python class."""
        if self.simple_module_path.exists():
            # Get real classes from our test module
            classes = InterfaceAnalyzer.return_classes_from_py(
                str(self.simple_module_path)
            )

            if classes:
                test_class = classes[0]  # Use first class found

                parent_command = UnifiedGraftModel(
                    RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
                )

                # Use the registered handler
                handler = self.handlers.analyzer_handler[UnifiedGraftModelType.TYPE_DEF]
                result = handler.generate_unified_graft_model(
                    test_class, parent_command, self.handlers
                )

                # Verify result
                self.assertIsInstance(result, UnifiedGraftModel)
                self.assertEqual(
                    result.graft_model_type, UnifiedGraftModelType.TYPE_DEF
                )

    def test_types_to_analyze_independence(self) -> None:
        """Test that types_to_analyze lists are independent between instances."""
        handlers1 = Handlers()
        handlers2 = Handlers()

        # Add items to first instance
        handlers1.types_to_analyze.append("test_class_1")
        handlers1.types_to_analyze.append("test_class_2")

        # Second instance should be empty (not shared)
        self.assertEqual(len(handlers2.types_to_analyze), 0)

        # Add to second instance
        handlers2.types_to_analyze.append("different_class")

        # First instance should not be affected
        self.assertEqual(len(handlers1.types_to_analyze), 2)
        self.assertNotIn("different_class", handlers1.types_to_analyze)

    def test_handler_instance_independence(self) -> None:
        """Test that handler instances are independent."""
        handlers1 = Handlers()
        handlers2 = Handlers()

        # Handlers should be different instances
        self.assertIsNot(
            handlers1.analyzer_handler[UnifiedGraftModelType.TYPE_DEF],
            handlers2.analyzer_handler[UnifiedGraftModelType.TYPE_DEF],
        )

        # But they should be the same type
        self.assertEqual(
            type(handlers1.analyzer_handler[UnifiedGraftModelType.TYPE_DEF]),
            type(handlers2.analyzer_handler[UnifiedGraftModelType.TYPE_DEF]),
        )

    def test_shared_handler_integration(self) -> None:
        """Test that shared handlers work correctly with analyzer handlers."""
        # Test that TYPE_USAGE handler is available and works
        type_usage_handler = self.handlers.shared_handler[
            UnifiedGraftModelType.TYPE_USAGE
        ]

        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Test with a real type
        result = type_usage_handler.generate_unified_graft_model(
            str, parent_command, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_USAGE)

    def test_parameters_array_handler_with_real_function(self) -> None:
        """Test PARAMETERS_ARRAY handler with real function."""

        def sample_function(a: int, b: str = "default", *args, **kwargs):
            pass

        parameters_handler = self.handlers.shared_handler[
            UnifiedGraftModelType.PARAMETERS_ARRAY
        ]

        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_METHOD, []
        )

        result = parameters_handler.generate_unified_graft_model(
            sample_function, parent_command, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(
            result.graft_model_type, UnifiedGraftModelType.PARAMETERS_ARRAY
        )

    def test_all_handlers_can_create_models(self) -> None:
        """Test that all handlers can create UnifiedGraftModel instances."""
        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Test analyzer handlers with appropriate test data
        test_data = {
            UnifiedGraftModelType.GLOBAL_METHOD: lambda: "test",
            UnifiedGraftModelType.GLOBAL_FIELD: {"name": "test_field"},
        }

        for model_type, test_object in test_data.items():
            if model_type in self.handlers.analyzer_handler:
                handler = self.handlers.analyzer_handler[model_type]

                # Prepare test object if it's a function
                if callable(test_object):
                    test_object.__name__ = "test_function"
                    test_object.params = []

                try:
                    result = handler.generate_unified_graft_model(
                        test_object, parent_command, self.handlers
                    )

                    self.assertIsInstance(
                        result,
                        UnifiedGraftModel,
                        f"Handler for {model_type} didn't return UnifiedGraftModel",
                    )
                    self.assertEqual(
                        result.graft_model_type,
                        model_type,
                        f"Handler for {model_type} returned wrong type",
                    )
                except Exception as e:
                    self.fail(f"Handler for {model_type} failed: {e}")

    def test_handler_error_handling(self) -> None:
        """Test that handlers handle edge cases gracefully."""
        parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

        # Test with None object (should not crash)
        global_method_handler = self.handlers.analyzer_handler[
            UnifiedGraftModelType.GLOBAL_METHOD
        ]

        try:
            # This might fail, but shouldn't crash the entire system
            result = global_method_handler.generate_unified_graft_model(
                None, parent_command, self.handlers
            )
            # If it succeeds, it should return a valid model
            if result:
                self.assertIsInstance(result, UnifiedGraftModel)
        except (AttributeError, TypeError):
            # Expected for None input
            pass


if __name__ == "__main__":
    unittest.main()
