"""
Real-case tests for SharedModuleHashHandler.
Tests module hash generation with actual Python objects and modules.
"""

import inspect
import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.shared.shared_module_hash_handler import (
    SharedModuleHashHandler,
)
from moduleanalyzer.test_resources.complex_module import (
    COMPLEX_GLOBAL_DATA,
    ComplexClass,
    timing_decorator,
)
from moduleanalyzer.test_resources.simple_module import (
    SIMPLE_CONSTANT,
    SimpleClass,
    simple_function,
)
from moduleanalyzer.test_resources.test_classes import (
    MY_GLOBAL_CONSTANT,
    SampleBClass,
    SampleClass,
    sample_global_function,
)


class TestSharedModuleHashHandler(unittest.TestCase):
    """Real-case test cases for SharedModuleHashHandler."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers."""
        self.handler = SharedModuleHashHandler()
        self.handlers = Handlers()
        self.parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

    def test_generate_unified_graft_model_with_real_class(self) -> None:
        """Test module hash generation with a real Python class."""
        # Use SampleClass from test_classes module
        test_class = SampleClass

        result = self.handler.generate_unified_graft_model(
            test_class, self.parent_command, self.handlers
        )

        # Verify result is the hash of the module name
        expected_module_name = test_class.__module__
        expected_hash = hash(expected_module_name)

        self.assertEqual(result, expected_hash)
        self.assertIsInstance(result, int)

        # Verify the module name is what we expect
        self.assertTrue(expected_module_name.endswith("test_classes"))

    def test_generate_unified_graft_model_with_real_function(self) -> None:
        """Test module hash generation with a real Python function."""
        # Use simple_function from simple_module
        test_function = simple_function

        result = self.handler.generate_unified_graft_model(
            test_function, self.parent_command, self.handlers
        )

        # Verify result is the hash of the module name
        expected_module_name = test_function.__module__
        expected_hash = hash(expected_module_name)

        self.assertEqual(result, expected_hash)
        self.assertIsInstance(result, int)

        # Verify the module name is what we expect
        self.assertTrue(expected_module_name.endswith("simple_module"))

    def test_generate_unified_graft_model_with_different_modules(self) -> None:
        """Test that objects from different modules produce different hashes."""
        # Objects from different modules
        simple_class = SimpleClass
        complex_class = ComplexClass

        simple_result = self.handler.generate_unified_graft_model(
            simple_class, self.parent_command, self.handlers
        )

        complex_result = self.handler.generate_unified_graft_model(
            complex_class, self.parent_command, self.handlers
        )

        # Results should be different since they're from different modules
        self.assertNotEqual(simple_result, complex_result)
        self.assertIsInstance(simple_result, int)
        self.assertIsInstance(complex_result, int)

    def test_generate_unified_graft_model_with_same_module_objects(self) -> None:
        """Test that objects from the same module produce the same hash."""
        # Objects from the same module (test_classes)
        test_class = SampleClass
        test_b_class = SampleBClass
        global_function = sample_global_function

        class_result = self.handler.generate_unified_graft_model(
            test_class, self.parent_command, self.handlers
        )

        class_b_result = self.handler.generate_unified_graft_model(
            test_b_class, self.parent_command, self.handlers
        )

        function_result = self.handler.generate_unified_graft_model(
            global_function, self.parent_command, self.handlers
        )

        # All should have the same hash since they're from the same module
        self.assertEqual(class_result, class_b_result)
        self.assertEqual(class_b_result, function_result)

    def test_generate_unified_graft_model_with_built_in_object(self) -> None:
        """Test module hash generation with built-in Python objects."""
        # Use built-in objects like str, int, list
        builtin_objects = [str, int, list, dict, len, print]

        for obj in builtin_objects:
            result = self.handler.generate_unified_graft_model(
                obj, self.parent_command, self.handlers
            )

            # Built-in objects should return the hash of 'builtins'
            expected_hash = hash("builtins")
            self.assertEqual(result, expected_hash)

    def test_generate_unified_graft_model_with_decorator(self) -> None:
        """Test module hash generation with decorated functions."""
        # Use timing_decorator from complex_module
        decorator_function = timing_decorator

        result = self.handler.generate_unified_graft_model(
            decorator_function, self.parent_command, self.handlers
        )

        # Verify result is the hash of the complex_module
        expected_module_name = decorator_function.__module__
        expected_hash = hash(expected_module_name)

        self.assertEqual(result, expected_hash)
        self.assertTrue(expected_module_name.endswith("complex_module"))

    def test_generate_unified_graft_model_with_global_variables(self) -> None:
        """Test module hash generation with global variables and constants."""
        # Test with different types of global objects
        global_objects = [MY_GLOBAL_CONSTANT, SIMPLE_CONSTANT, COMPLEX_GLOBAL_DATA]

        for global_obj in global_objects:
            # For primitive types, inspect.getmodule returns None
            # So we expect "null" return value
            result = self.handler.generate_unified_graft_model(
                global_obj, self.parent_command, self.handlers
            )

            # Global variables (primitive types) should return "null"
            # since inspect.getmodule returns None for them
            self.assertEqual(result, "null")

    def test_generate_unified_graft_model_with_method_objects(self) -> None:
        """Test module hash generation with instance and class methods."""
        # Create an instance to test with
        test_instance = SampleClass(42)

        # Test with bound methods
        bound_method = test_instance.multiply_two_numbers
        static_method = SampleClass.multiply_by_two
        class_method = SampleClass.create_with_defaults

        method_objects = [bound_method, static_method, class_method]

        for method_obj in method_objects:
            result = self.handler.generate_unified_graft_model(
                method_obj, self.parent_command, self.handlers
            )

            # All methods should have the same module hash as their class
            expected_module_name = SampleClass.__module__
            expected_hash = hash(expected_module_name)

            self.assertEqual(result, expected_hash)

    def test_generate_unified_graft_model_consistency(self) -> None:
        """Test that the same object always produces the same hash."""
        test_obj = SimpleClass

        # Call multiple times
        results = []
        for _ in range(5):
            result = self.handler.generate_unified_graft_model(
                test_obj, self.parent_command, self.handlers
            )
            results.append(result)

        # All results should be identical
        self.assertTrue(all(r == results[0] for r in results))

        # And should match the expected hash
        expected_hash = hash(test_obj.__module__)
        self.assertEqual(results[0], expected_hash)

    def test_module_name_extraction_accuracy(self) -> None:
        """Test that module names are correctly extracted and hashed."""
        test_cases = [
            (SampleClass, "test_classes"),
            (SimpleClass, "simple_module"),
            (ComplexClass, "complex_module"),
            (simple_function, "simple_module"),
            (timing_decorator, "complex_module"),
        ]

        for obj, expected_module_suffix in test_cases:
            result = self.handler.generate_unified_graft_model(
                obj, self.parent_command, self.handlers
            )

            # Verify the module name ends with expected suffix
            actual_module = inspect.getmodule(obj)
            self.assertIsNotNone(actual_module)
            self.assertTrue(actual_module.__name__.endswith(expected_module_suffix))

            # Verify hash matches
            expected_hash = hash(actual_module.__name__)
            self.assertEqual(result, expected_hash)
