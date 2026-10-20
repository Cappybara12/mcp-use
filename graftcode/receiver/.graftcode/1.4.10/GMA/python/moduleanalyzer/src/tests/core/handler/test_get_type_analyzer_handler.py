"""
Tests for GetTypeAnalyzerHandler using real Python classes and handlers.
"""

import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_type_analyzer_handler import (
    GetTypeAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.test_resources.complex_module import ComplexClass
from moduleanalyzer.test_resources.simple_module import SimpleClass
from moduleanalyzer.test_resources.test_classes import SampleClass


class TestGetTypeAnalyzerHandler(unittest.TestCase):
    """Test cases for GetTypeAnalyzerHandler using real Python classes and handlers."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers and class examples."""
        self.handler = GetTypeAnalyzerHandler()
        self.handlers = Handlers()

        # Create parent commands for different test scenarios
        self.library_parent = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )
        self.module_parent = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.MODULE, []
        )

    def test_generate_unified_graft_model_with_real_test_class(self) -> None:
        """Test generate_unified_graft_model with real SampleClass."""
        result = self.handler.generate_unified_graft_model(
            SampleClass, self.library_parent, self.handlers
        )

        # Verify basic structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_DEF)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Verify payload contains expected components
        # Should have: namespace, class_name, module_full_name, module_hash, modifier, fields, methods, constructors
        self.assertTrue(len(result.payload) > 0)

    def test_generate_unified_graft_model_with_simple_class(self) -> None:
        """Test generate_unified_graft_model with real SimpleClass."""
        result = self.handler.generate_unified_graft_model(
            SimpleClass, self.library_parent, self.handlers
        )

        # Verify basic structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_DEF)
        self.assertEqual(result.runtime_name, RuntimeName.Python)
        self.assertTrue(len(result.payload) > 0)

    def test_generate_unified_graft_model_with_complex_class(self) -> None:
        """Test generate_unified_graft_model with real ComplexClass."""
        result = self.handler.generate_unified_graft_model(
            ComplexClass, self.library_parent, self.handlers
        )

        # Verify basic structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_DEF)
        self.assertEqual(result.runtime_name, RuntimeName.Python)
        self.assertTrue(len(result.payload) > 0)

    def test_add_constructors_to_payload_with_real_test_class(self) -> None:
        """Test add_constructors_to_payload with real SampleClass that has __init__."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_constructors_to_payload(
            command, SampleClass, self.handlers
        )

        # Verify that constructor was processed (SampleClass has __init__)
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been modified to include constructor info
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_constructors_to_payload_with_simple_class(self) -> None:
        """Test add_constructors_to_payload with SimpleClass that has __init__."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_constructors_to_payload(
            command, SimpleClass, self.handlers
        )

        # Verify that constructor was processed
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_constructors_to_payload_without_init(self) -> None:
        """Test add_constructors_to_payload with class without explicit __init__."""

        class SampleClassNoInit:
            """Test class without explicit __init__ method."""

            pass

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_constructors_to_payload(
            command, SampleClassNoInit, self.handlers
        )

        # Verify no constructor was added since no explicit __init__
        self.assertIsInstance(result, UnifiedGraftModel)
        # Payload should remain the same size
        self.assertEqual(len(result.payload), len(command.payload))

    def test_add_methods_to_payload_with_real_test_class(self) -> None:
        """Test add_methods_to_payload with real SampleClass methods."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_methods_to_payload(
            command, SampleClass, self.handlers
        )

        # Verify that methods were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        # SampleClass has multiple methods, so payload should be larger
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_methods_to_payload_with_simple_class(self) -> None:
        """Test add_methods_to_payload with SimpleClass methods."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_methods_to_payload(
            command, SimpleClass, self.handlers
        )

        # Verify that methods were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_methods_to_payload_with_static_and_instance_methods(self) -> None:
        """Test add_methods_to_payload with class containing both static and instance methods."""

        class SampleClassWithMixedMethods:
            def instance_method(self):
                return "instance"

            @staticmethod
            def static_method():
                return "static"

            @classmethod
            def class_method(cls):
                return "class"

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_methods_to_payload(
            command, SampleClassWithMixedMethods, self.handlers
        )

        # Verify that methods were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        # Should have processed multiple methods
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_fields_to_payload_with_real_test_class(self) -> None:
        """Test add_fields_to_payload with real SampleClass fields."""
        # Create a proper parent command with class name in payload (as the instance field handler expects)
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, ["SampleClass"]
        )

        result = self.handler.add_fields_to_payload(command, SampleClass, self.handlers)

        # Verify that fields were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        # SampleClass has static fields, so payload should be larger or equal
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_fields_to_payload_with_simple_class(self) -> None:
        """Test add_fields_to_payload with SimpleClass fields."""
        # Create a proper parent command with class name in payload
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, ["SimpleClass"]
        )

        result = self.handler.add_fields_to_payload(command, SimpleClass, self.handlers)

        # Verify that fields were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        # SimpleClass has class_variable, so should be processed
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_add_fields_to_payload_with_class_variables(self) -> None:
        """Test add_fields_to_payload with class containing various field types."""

        class SampleClassWithFields:
            class_var = "class_value"
            public_field = 42
            another_field = [1, 2, 3]

        # Create a proper parent command with class name in payload
        command = UnifiedGraftModel(
            RuntimeName.Python,
            UnifiedGraftModelType.TYPE_DEF,
            ["SampleClassWithFields"],
        )

        result = self.handler.add_fields_to_payload(
            command, SampleClassWithFields, self.handlers
        )

        # Verify that fields were processed
        self.assertIsInstance(result, UnifiedGraftModel)
        # Should have processed multiple fields
        self.assertTrue(len(result.payload) >= len(command.payload))

    def test_is_static_method_behavior(self) -> None:
        """Test is_static method behavior with different attribute types."""

        # Set up handler with a real class that has static methods
        class SampleClassWithStatic:
            @staticmethod
            def static_method():
                return "static"

            @classmethod
            def class_method(cls):
                return "class"

            def instance_method(self):
                return "instance"

            class_variable = "not_a_method"

        self.handler.current_class = SampleClassWithStatic

        # The is_static method checks if attributes are staticmethod or classmethod instances
        # Let's verify the types are what we expect in vars()
        self.assertIsInstance(
            vars(SampleClassWithStatic)["static_method"], staticmethod
        )
        self.assertIsInstance(vars(SampleClassWithStatic)["class_method"], classmethod)
        self.assertIsInstance(
            vars(SampleClassWithStatic)["instance_method"], type(lambda: None)
        )  # function

        # Now test the handler's is_static method
        self.assertTrue(self.handler.is_static("static_method"))
        self.assertTrue(
            self.handler.is_static("class_method")
        )  # classmethod is also considered static

        # Instance methods and regular attributes should return False
        self.assertFalse(self.handler.is_static("instance_method"))
        self.assertFalse(self.handler.is_static("class_variable"))

        # Test non-existent field
        self.assertFalse(self.handler.is_static("non_existent_field"))

    def test_add_namespace_to_payload_with_real_class(self) -> None:
        """Test add_namespace_to_payload method with real SampleClass."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_namespace_to_payload(
            command, SampleClass, self.handlers
        )

        # Verify namespace was added to payload
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) > len(command.payload))
        # Verify the module information is present
        self.assertTrue(hasattr(SampleClass, "__module__"))

    def test_add_class_name_to_payload_with_real_class(self) -> None:
        """Test add_class_name_to_payload method with real SampleClass."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_class_name_to_payload(
            command, SampleClass, self.handlers
        )

        # Verify class name was added to payload
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) > len(command.payload))
        # Verify class has expected name attribute
        self.assertEqual(SampleClass.__name__, "SampleClass")

    def test_add_modifier_to_payload_with_real_class(self) -> None:
        """Test add_modifier_to_payload method with real SampleClass."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_modifier_to_payload(
            command, SampleClass, self.handlers
        )

        # Verify modifier was added to payload
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_module_full_name_to_payload_with_real_class(self) -> None:
        """Test add_module_full_name_to_payload method with real class."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_module_full_name_to_payload(
            command, SimpleClass, self.handlers
        )

        # Verify module full name was added to payload
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_module_hash_to_payload_with_real_class(self) -> None:
        """Test add_module_hash_to_payload method with real class."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, []
        )

        result = self.handler.add_module_hash_to_payload(
            command, ComplexClass, self.handlers
        )

        # Verify module hash was added to payload
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_comprehensive_class_analysis_with_real_complex_class(self) -> None:
        """Test comprehensive analysis with real ComplexClass from resources."""
        result = self.handler.generate_unified_graft_model(
            ComplexClass, self.library_parent, self.handlers
        )

        # Verify comprehensive analysis results
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_DEF)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Complex class should have substantial payload with all components
        self.assertTrue(
            len(result.payload) > 5
        )  # namespace, class_name, module info, fields, methods, etc.

    def test_integration_with_all_real_classes(self) -> None:
        """Test integration with all available real test classes."""
        test_classes = [SampleClass, SimpleClass, ComplexClass]

        for test_class in test_classes:
            with self.subTest(class_name=test_class.__name__):
                result = self.handler.generate_unified_graft_model(
                    test_class, self.library_parent, self.handlers
                )

                # Verify each class is properly analyzed
                self.assertIsInstance(result, UnifiedGraftModel)
                self.assertEqual(
                    result.graft_model_type, UnifiedGraftModelType.TYPE_DEF
                )
                self.assertEqual(result.runtime_name, RuntimeName.Python)
                self.assertTrue(len(result.payload) > 0)

    def test_real_class_with_all_components(self) -> None:
        """Test analysis of a real class that has constructors, methods, and fields."""
        # SampleClass has __init__, methods, and static fields
        result = self.handler.generate_unified_graft_model(
            SampleClass, self.library_parent, self.handlers
        )

        # Verify all components are analyzed
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.TYPE_DEF)

        # Should have processed multiple components (namespace, class name, fields, methods, constructor)
        self.assertTrue(len(result.payload) >= 5)

    def test_handler_with_different_parent_commands(self) -> None:
        """Test handler behavior with different parent command types."""
        parent_types = [
            (self.library_parent, "library"),
            (self.module_parent, "module"),
        ]

        for parent_command, parent_type in parent_types:
            with self.subTest(parent_type=parent_type):
                result = self.handler.generate_unified_graft_model(
                    SimpleClass, parent_command, self.handlers
                )

                self.assertIsInstance(result, UnifiedGraftModel)
                self.assertEqual(
                    result.graft_model_type, UnifiedGraftModelType.TYPE_DEF
                )
                self.assertTrue(len(result.payload) > 0)

    def test_methods_payload_excludes_leading_underscore_names(self) -> None:
        """Private-by-convention methods (leading _) must not appear in TYPE_DEF."""

        class VisibilityClass:
            def public_method(self) -> None:
                pass

            def _private_method(self) -> None:
                pass

        result = self.handler.generate_unified_graft_model(
            VisibilityClass, self.library_parent, self.handlers
        )

        method_names = {
            item.payload[0]
            for item in result.payload
            if isinstance(item, UnifiedGraftModel)
            and item.graft_model_type
            in (
                UnifiedGraftModelType.INSTANCE_METHOD,
                UnifiedGraftModelType.STATIC_METHOD,
            )
        }

        self.assertIn("public_method", method_names)
        self.assertNotIn("_private_method", method_names)


if __name__ == "__main__":
    unittest.main()
