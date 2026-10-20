from typing import Any, Optional, get_args

from graftcode_protocol.enums.graft_code_primitive_type import (
    GraftCodePrimitiveType,
)
from graftcode_protocol.enums.is_nullable import IsNullable
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from .shared_type_handler import SharedTypeHandler, TypeWithNullable

class SharedArrayTypeHandler(SharedTypeHandler):
    """
    Handler for array types.
    Matches netcore's SharedArrayTypeHandler implementation.
    
    Structure: TYPE_USAGE → TYPE_USAGE_ARRAY → [IS_NULLABLE, ARRAY_DIMENSION, TYPE_USAGE (element type)]
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for array types.
        
        Structure matches C#:
        - TYPE_USAGE wrapper (created by SharedTypeHandler)
        - TYPE_USAGE_ARRAY with payload: [IS_NULLABLE, ARRAY_DIMENSION, <nested type> (element type)]
        Note: Element type is a nested type directly, NOT wrapped in TYPE_USAGE.

        :param analyzed_object: The object being analyzed.
        :param _parent_command: The parent command related to the object (unused, can be None).
        :param handlers: A collection of handlers that contains current_library_name
                         for external type detection.
        :return: A UnifiedGraftModel instance representing the type of the
                 analyzed object.
        """
        # Get current library name for external type detection
        current_library_name = None
        if handlers and hasattr(handlers, "current_library_name"):
            current_library_name = handlers.current_library_name

        # Extract type and nullable state from TypeWithNullable wrapper if present
        if isinstance(analyzed_object, TypeWithNullable):
            type_obj = analyzed_object.type
            is_nullable = analyzed_object.is_nullable
        else:
            type_obj = analyzed_object
            is_nullable = self._get_is_nullable(analyzed_object)
        
        # Calculate array dimensions and element type
        # For nested arrays like List[List[int]], we need to create nested TYPE_USAGE_ARRAY structures
        array_dimensions = 1  # Default to 1D
        element_type_obj = type_obj
        
        # Handle List[T] types
        if self._is_list_type(type_obj):
            args = get_args(type_obj)
            if args:
                element_type_obj = args[0]
                # Check for nested lists (jagged arrays)
                # For nested arrays, we create nested TYPE_USAGE_ARRAY structures
                if self._is_list_type(element_type_obj):
                    # This is a nested array - keep element_type_obj as List[int] to create nested structure
                    # The recursive call in _generate_element_type_usage will handle creating the inner array
                    # Set dimension to 2 for the outer array (total nesting depth)
                    array_dimensions = 2
                    # element_type_obj remains as List[int], which will be processed recursively
                else:
                    # Single-level array, element_type_obj is already the element type
                    pass
            else:
                element_type_obj = Any
        # Handle string-based type names with [] notation
        elif isinstance(type_obj, str) and "[]" in type_obj:
            array_dimensions = type_obj.count("[]")
            element_type_name = type_obj.replace("[]", "").strip()
            # Map string names to types
            if element_type_name == "int":
                element_type_obj = int
            elif element_type_name == "str":
                element_type_obj = str
            elif element_type_name == "float":
                element_type_obj = float
            elif element_type_name == "bool":
                element_type_obj = bool
            else:
                element_type_obj = element_type_name

        # Generate nested type for element (NOT wrapped in TYPE_USAGE - only top-level entry point uses TYPE_USAGE)
        element_type_usage = self._generate_element_type_usage(
            element_type_obj, _parent_command, handlers, current_library_name
        )

        # Create TYPE_USAGE_ARRAY with payload: [IS_NULLABLE, ARRAY_DIMENSION, TYPE_USAGE]
        # Note: TYPE_USAGE wrapper is created by SharedTypeHandler, not here
        array_type = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_ARRAY, []
        )
        array_type = array_type.add_arg_to_payload(is_nullable.value)
        array_type = array_type.add_arg_to_payload(array_dimensions)
        array_type = array_type.add_arg_to_payload(element_type_usage)
        
        return array_type
    
    def _generate_element_type_usage(
        self,
        element_type_obj: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
        current_library_name: Optional[str],
    ) -> UnifiedGraftModel:
        """
        Recursively generate nested type for array element (NOT wrapped in TYPE_USAGE).
        TYPE_USAGE is only the top-level entry point.
        """
        # Use the main type handler's internal method to generate nested type directly
        # (without TYPE_USAGE wrapper)
        type_handler = handlers.shared_handler.get(UnifiedGraftModelType.TYPE_USAGE)
        if type_handler and hasattr(type_handler, "_generate_unified_graft_model_for_type"):
            return type_handler._generate_unified_graft_model_for_type(
                element_type_obj, _parent_command, handlers, IsNullable.FALSE
            )
        # Fallback: create primitive type directly
        return UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE, []
        )
