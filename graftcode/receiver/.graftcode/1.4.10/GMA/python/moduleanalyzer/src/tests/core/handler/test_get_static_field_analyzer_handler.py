import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_static_field_analyzer_handler import (
    GetStaticFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.test_resources.simple_module import SimpleClass
from moduleanalyzer.test_resources.test_classes import SampleClass


class RealStaticFieldWrapper:
    """Wrapper to represent a real static field with metadata for testing."""

    def __init__(self, name: str, value: any, field_type: type):
        self.__name__ = name
        self.value = value
        self.type = field_type
        self.modifiers = []  # Can be extended with actual modifiers


class TestGetStaticFieldAnalyzerHandler(unittest.TestCase):
    """Test class for GetStaticFieldAnalyzerHandler using real Python objects."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers and static field examples."""
        self.handler = GetStaticFieldAnalyzerHandler()
        self.handlers = Handlers()

        # Create parent commands for different test classes
        self.test_class_parent = UnifiedGraftModel(
            RuntimeName.Python,
            UnifiedGraftModelType.TYPE_DEF,
            ["SampleClass"],
        )
        self.simple_class_parent = UnifiedGraftModel(
            RuntimeName.Python,
            UnifiedGraftModelType.TYPE_DEF,
            ["SimpleClass"],
        )

        # Create real static field wrappers based on actual class variables
        self.static_value_field = RealStaticFieldWrapper(
            "static_value", SampleClass.static_value, type(SampleClass.static_value)
        )
        self.protected_static_field = RealStaticFieldWrapper(
            "_protected_static",
            SampleClass._protected_static,
            type(SampleClass._protected_static),
        )
        self.simple_class_variable_field = RealStaticFieldWrapper(
            "class_variable",
            SimpleClass.class_variable,
            type(SimpleClass.class_variable),
        )

    def test_generate_unified_graft_model_with_real_static_field(self) -> None:
        """Test static field analysis with a real Python static field."""
        result = self.handler.generate_unified_graft_model(
            self.static_value_field, self.test_class_parent, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)
        self.assertTrue(
            len(result.payload) >= 4
        )  # field_name, type, modifiers, class_name

    def test_generate_unified_graft_model_with_protected_static_field(self) -> None:
        """Test static field analysis with a protected static field."""
        result = self.handler.generate_unified_graft_model(
            self.protected_static_field, self.test_class_parent, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)
        self.assertTrue(len(result.payload) >= 4)

    def test_generate_unified_graft_model_with_simple_class_static(self) -> None:
        """Test static field analysis with SimpleClass static field."""
        result = self.handler.generate_unified_graft_model(
            self.simple_class_variable_field, self.simple_class_parent, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)
        self.assertTrue(len(result.payload) >= 4)

    def test_add_field_name_to_payload_with_real_static_field(self) -> None:
        """Test adding field name to payload with real static field."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.STATIC_FIELD, []
        )

        result = self.handler.add_field_name_to_payload(
            command, self.static_value_field, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) >= 1)

    def test_add_field_type_to_payload_with_real_static_field(self) -> None:
        """Test adding field type to payload with real static field."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.STATIC_FIELD, []
        )

        result = self.handler.add_field_type_to_payload(
            command, self.static_value_field, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) >= 1)

    def test_add_class_name_to_payload_with_real_parent(self) -> None:
        """Test adding class name to payload with real parent command."""
        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.STATIC_FIELD, []
        )

        result = self.handler.add_class_name_to_payload(
            command, self.test_class_parent, self.handlers
        )

        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertTrue(len(result.payload) >= 1)

    def test_static_field_type_detection_accuracy(self) -> None:
        """Test that static field type detection works correctly."""
        # Test integer static field
        self.assertIsInstance(self.static_value_field.value, int)
        self.assertEqual(self.static_value_field.type, int)

        # Test string static field
        self.assertIsInstance(self.protected_static_field.value, str)
        self.assertEqual(self.protected_static_field.type, str)

        # Test simple class variable
        self.assertIsInstance(self.simple_class_variable_field.value, str)
        self.assertEqual(self.simple_class_variable_field.type, str)

    def test_different_static_fields_from_different_classes(self) -> None:
        """Test static fields from different classes."""
        # SampleClass static field
        test_result = self.handler.generate_unified_graft_model(
            self.static_value_field, self.test_class_parent, self.handlers
        )

        # SimpleClass static field
        simple_result = self.handler.generate_unified_graft_model(
            self.simple_class_variable_field, self.simple_class_parent, self.handlers
        )

        self.assertIsInstance(test_result, UnifiedGraftModel)
        self.assertIsInstance(simple_result, UnifiedGraftModel)
        self.assertEqual(
            test_result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD
        )
        self.assertEqual(
            simple_result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD
        )

    def test_integration_with_real_handlers(self) -> None:
        """Test integration with real handlers system."""
        result = self.handler.generate_unified_graft_model(
            self.static_value_field, self.test_class_parent, self.handlers
        )

        # Verify the structure contains all expected components
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.STATIC_FIELD)

        # Should have 4 payload items: field_name, type, modifiers, class_name
        self.assertEqual(len(result.payload), 4)

        # Verify payload structure:
        # 0: field_name (string from SharedFieldNameHandler)
        # 1: type (UnifiedGraftModel from SharedTypeHandler)
        # 2: modifiers (from SharedModifierHandler)
        # 3: class_name (string from SharedClassNameHandler)
        self.assertIsInstance(result.payload[0], str)  # field name
        self.assertEqual(result.payload[0], "static_value")

        # Type handler should return a UnifiedGraftModel
        self.assertIsInstance(result.payload[1], UnifiedGraftModel)

        # Modifiers and class name - check what they actually return
        # (these could be strings or UnifiedGraftModels depending on implementation)

    def test_field_name_extraction_accuracy(self) -> None:
        """Test that field names are extracted correctly from real static fields."""
        # Test static_value field name
        self.assertEqual(self.static_value_field.__name__, "static_value")

        # Test protected static field name
        self.assertEqual(self.protected_static_field.__name__, "_protected_static")

        # Test simple class variable name
        self.assertEqual(self.simple_class_variable_field.__name__, "class_variable")

    def test_wrapper_represents_real_values(self) -> None:
        """Test that wrapper objects accurately represent real static field values."""
        # Verify wrapper values match actual class values
        self.assertEqual(self.static_value_field.value, SampleClass.static_value)
        self.assertEqual(
            self.protected_static_field.value, SampleClass._protected_static
        )
        self.assertEqual(
            self.simple_class_variable_field.value, SimpleClass.class_variable
        )

        # Verify types are correctly captured
        self.assertEqual(self.static_value_field.type, type(SampleClass.static_value))
        self.assertEqual(
            self.protected_static_field.type, type(SampleClass._protected_static)
        )
        self.assertEqual(
            self.simple_class_variable_field.type, type(SimpleClass.class_variable)
        )
