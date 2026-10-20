"""
Real-case tests for GetGlobalFieldAnalyzerHandler.
Tests global field analysis with actual Python objects and variables.
"""

import unittest

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.get_global_field_analyzer_handler import (
    GetGlobalFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.test_resources.complex_module import (
    COMPLEX_GLOBAL_DATA,
    complex_global_function,
)
from moduleanalyzer.test_resources.simple_module import (
    SIMPLE_CONSTANT,
    simple_list,
    simple_variable,
)
from moduleanalyzer.test_resources.test_classes import (
    MY_GLOBAL_CONSTANT,
    my_global_dict,
    my_global_list,
    my_global_variable,
)


class TestGetGlobalFieldAnalyzerHandler(unittest.TestCase):
    """Real-case test cases for GetGlobalFieldAnalyzerHandler."""

    def setUp(self) -> None:
        """Set up test fixtures with real handlers."""
        self.handler = GetGlobalFieldAnalyzerHandler()
        self.handlers = Handlers()
        self.parent_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.LIBRARY, []
        )

    def test_generate_unified_graft_model_with_string_constant(self) -> None:
        """Test global field analysis with a real string constant."""
        # Use MY_GLOBAL_CONSTANT from test_classes
        global_field = MY_GLOBAL_CONSTANT

        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Verify the result has the expected payload structure (field name, type, modifiers)
        self.assertTrue(len(result.payload) >= 3)

    def test_generate_unified_graft_model_with_integer_variable(self) -> None:
        """Test global field analysis with a real integer variable."""
        # Use my_global_variable from test_classes
        global_field = my_global_variable

        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

        # Verify the result has the expected payload structure
        self.assertTrue(len(result.payload) >= 3)

    def test_generate_unified_graft_model_with_list_variable(self) -> None:
        """Test global field analysis with a real list variable."""
        # Use my_global_list from test_classes
        global_field = my_global_list

        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

    def test_generate_unified_graft_model_with_dict_variable(self) -> None:
        """Test global field analysis with a real dictionary variable."""
        # Use my_global_dict from test_classes
        global_field = my_global_dict

        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

    def test_generate_unified_graft_model_with_complex_data(self) -> None:
        """Test global field analysis with complex nested data structure."""
        # Use COMPLEX_GLOBAL_DATA from complex_module
        global_field = COMPLEX_GLOBAL_DATA

        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify result structure
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertEqual(result.runtime_name, RuntimeName.Python)

    def test_add_field_name_to_payload_with_real_object(self) -> None:
        """Test add_field_name_to_payload method with real object."""
        # Use a real object with name
        global_field = complex_global_function

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_FIELD, []
        )

        # Execute
        result = self.handler.add_field_name_to_payload(
            command, global_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with field name information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_type_to_payload_with_string(self) -> None:
        """Test add_field_type_to_payload method with real string."""
        # Use a real string field
        global_field = SIMPLE_CONSTANT

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_FIELD, []
        )

        # Execute
        result = self.handler.add_field_type_to_payload(
            command, global_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with type information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_type_to_payload_with_integer(self) -> None:
        """Test add_field_type_to_payload method with real integer."""
        # Use a real integer field
        global_field = simple_variable

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_FIELD, []
        )

        # Execute
        result = self.handler.add_field_type_to_payload(
            command, global_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with type information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_type_to_payload_with_list(self) -> None:
        """Test add_field_type_to_payload method with real list."""
        # Use a real list field
        global_field = simple_list

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_FIELD, []
        )

        # Execute
        result = self.handler.add_field_type_to_payload(
            command, global_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with type information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_add_field_modifiers_to_payload_with_real_object(self) -> None:
        """Test add_field_modifiers_to_payload method with real object."""
        # Use a real object
        global_field = MY_GLOBAL_CONSTANT

        command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GLOBAL_FIELD, []
        )

        # Execute
        result = self.handler.add_field_modifiers_to_payload(
            command, global_field, self.handlers
        )

        # Verify
        self.assertIsInstance(result, UnifiedGraftModel)
        # The payload should have been updated with modifier information
        self.assertTrue(len(result.payload) > len(command.payload))

    def test_field_type_detection_accuracy(self) -> None:
        """Test that field types are correctly detected for different data types."""
        test_cases = [
            (MY_GLOBAL_CONSTANT, "str"),
            (my_global_variable, "int"),
            (my_global_list, "list"),
            (my_global_dict, "dict"),
            (COMPLEX_GLOBAL_DATA, "dict"),
            (complex_global_function, "function"),
        ]

        for field_value, expected_type in test_cases:
            with self.subTest(field_value=field_value, expected_type=expected_type):
                # Test that type detection works correctly
                actual_type = type(field_value).__name__
                self.assertEqual(actual_type, expected_type)

                # Test the handler with this field
                result = self.handler.generate_unified_graft_model(
                    field_value, self.parent_command, self.handlers
                )

                self.assertIsInstance(result, UnifiedGraftModel)
                self.assertEqual(
                    result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD
                )

    def test_different_modules_global_fields(self) -> None:
        """Test global fields from different modules."""
        # Fields from different modules
        test_fields = [
            MY_GLOBAL_CONSTANT,  # from test_classes
            SIMPLE_CONSTANT,  # from simple_module
            COMPLEX_GLOBAL_DATA,  # from complex_module
        ]

        results = []
        for field in test_fields:
            result = self.handler.generate_unified_graft_model(
                field, self.parent_command, self.handlers
            )
            results.append(result)

            # Each should be a valid global field UGM
            self.assertIsInstance(result, UnifiedGraftModel)
            self.assertEqual(
                result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD
            )

        # All results should be valid but may have different content
        self.assertEqual(len(results), len(test_fields))

    def test_integration_with_real_handlers(self) -> None:
        """Test integration with real shared handlers."""
        # Use a real field
        global_field = my_global_list

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

        # Execute the analysis
        result = self.handler.generate_unified_graft_model(
            global_field, self.parent_command, self.handlers
        )

        # Verify the result is properly structured
        self.assertIsInstance(result, UnifiedGraftModel)
        self.assertEqual(result.graft_model_type, UnifiedGraftModelType.GLOBAL_FIELD)
        self.assertTrue(
            len(result.payload) >= 3
        )  # Should have field name, type, and modifiers


if __name__ == "__main__":
    unittest.main()
