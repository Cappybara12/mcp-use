"""
Real-case tests for GetInstanceFieldAnalyzerHandler.
Tests instance field analysis with actual Python class instances and fields.
"""

import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_instance_field_analyzer_handler import (
    GetInstanceFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.test_resources.complex_module import ComplexClass
from moduleanalyzer.test_resources.simple_module import SimpleClass
from moduleanalyzer.test_resources.test_classes import SampleClass


class TestGetInstanceFieldAnalyzerHandler(unittest.TestCase):
    """Real-case test cases for GetInstanceFieldAnalyzerHandler."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers."""
        self.handler = GetInstanceFieldAnalyzerHandler()
        self.handlers = Handlers()

        # Create real test instances
        self.test_instance = SampleClass(42, "test")
        self.simple_instance = SimpleClass("simple_test")
        self.complex_instance = ComplexClass([1, 2, 3])

        # Create parent commands with real class names
        self.test_class_parent = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, ["SampleClass"]
        )
        self.simple_class_parent = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, ["SimpleClass"]
        )
        self.complex_class_parent = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_DEF, ["ComplexClass"]
        )

    def test_generate_unified_graft_model_with_real_instance_field(self) -> None:
        """Test instance field analysis with a real class instance field."""
        # Use the public_value field from SampleClass instance
        instance_field = self.test_instance.public_value

        result = self.handler.generate_unified_graft_model(
            instance_field, self.test_class_parent, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.INSTANCE_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Verify the result has the expected payload structure
        self.assertTrue(
            len(result.payload) >= 4
        )  # field name, type, modifiers, class name

    def test_add_field_name_to_payload_with_real_field(self) -> None:
        """Test add_field_name_to_payload method with real field."""
        # Use a real field value
        instance_field = self.test_instance.public_value

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.INSTANCE_FIELD, []
        )

        # Execute
        result = self.handler.add_field_name_to_payload(
            command, instance_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with field name information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_type_to_payload_with_integer_field(self) -> None:
        """Test add_field_type_to_payload method with integer field."""
        # Use an integer field
        instance_field = self.test_instance.public_value  # This is an int

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.INSTANCE_FIELD, []
        )

        # Execute
        result = self.handler.add_field_type_to_payload(
            command, instance_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with type information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_modifiers_to_payload_with_real_field(self) -> None:
        """Test add_field_modifiers_to_payload method with real field."""
        # Use a real field
        instance_field = self.test_instance.public_value

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.INSTANCE_FIELD, []
        )

        # Execute
        result = self.handler.add_field_modifiers_to_payload(
            command, instance_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with modifier information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_class_name_to_payload_with_real_parent(self) -> None:
        """Test add_class_name_to_payload method with real parent command."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.INSTANCE_FIELD, []
        )

        # Execute with real parent command
        result = self.handler.add_class_name_to_payload(
            command, self.test_class_parent, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with class name information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_integration_with_real_handlers(self) -> None:
        """Test integration with real shared handlers."""
        # Use a real field
        instance_field = self.test_instance.public_value

        # Verify that the handlers are properly initialized
        self.assertIsNotNone(
            self.handlers.shared_handler.get(UnifiedGraftModelType.FIELD_NAME)
        )
        self.assertIsNotNone(
            self.handlers.shared_handler.get(UnifiedGraftModelType.TYPE_USAGE)
        )
        self.assertIsNotNone(
            self.handlers.shared_handler.get(UnifiedGraftModelType.MODIFIER)
        )
        self.assertIsNotNone(
            self.handlers.shared_handler.get(UnifiedGraftModelType.CLASS_NAME)
        )

        # Execute the analysis
        result = self.handler.generate_unified_graft_model(
            instance_field, self.test_class_parent, self.handlers
        )

        # Verify the result is properly structured
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.INSTANCE_FIELD)
        self.assertTrue(
            len(result.payload) >= 4
        )  # Should have field name, type, modifiers, and class name


if __name__ == "__main__":
    unittest.main()
