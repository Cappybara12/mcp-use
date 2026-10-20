from typing import Any, Optional, get_args, get_origin

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


class SharedGenericTypeHandler(SharedTypeHandler):
    """
    Handler for generic types.
    Matches netcore's SharedGenericTypeHandler implementation.
    
    Structure: TYPE_USAGE → TYPE_USAGE_GENERIC → [IS_NULLABLE, TYPE_USAGE (generic type), TYPE_USAGE[] (generic arguments)]
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for generic types.
        
        Structure matches C#:
        - TYPE_USAGE wrapper (created by SharedTypeHandler)
        - TYPE_USAGE_GENERIC with payload: [IS_NULLABLE, <nested type> (generic type itself), <nested type>[] (generic arguments)]
        Note: Generic type and arguments are nested types directly, NOT wrapped in TYPE_USAGE.

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
        
        origin = get_origin(type_obj)
        if origin is None:
            # Fallback if not a generic type
            primitive_handler = handlers.shared_handler.get(UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE)
            if primitive_handler:
                return primitive_handler.generate_unified_graft_model(
                    type_obj, _parent_command, handlers
                )
            # Return empty TYPE_USAGE_GENERIC as fallback
            return UnifiedGraftModel(
                RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_GENERIC, []
            )
        
        # Get normalized generic type name (e.g., "List`1" -> "List")
        normalized_name = getattr(origin, "__name__", str(origin))
        if "`" in normalized_name:
            normalized_name = normalized_name.split("`")[0]
        
        # Generate TYPE_USAGE for the generic type itself (e.g., List)
        generic_type_usage = self._generate_generic_type_usage(
            origin, _parent_command, handlers, current_library_name
        )
        
        # Get generic arguments
        args = get_args(type_obj)
        generic_args_usage = []
        for arg_type in args:
            arg_usage = self._generate_generic_type_usage(
                arg_type, _parent_command, handlers, current_library_name
            )
            generic_args_usage.append(arg_usage)
        
        # Create TYPE_USAGE_GENERIC with payload: [IS_NULLABLE, TYPE_USAGE (generic type), TYPE_USAGE[] (args)]
        # Note: TYPE_USAGE wrapper is created by SharedTypeHandler, not here
        generic_type = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_GENERIC, []
        )
        generic_type = generic_type.add_arg_to_payload(is_nullable.value)
        generic_type = generic_type.add_arg_to_payload(generic_type_usage)
        # Add all generic argument TYPE_USAGEs
        for arg_usage in generic_args_usage:
            generic_type = generic_type.add_arg_to_payload(arg_usage)
        
        return generic_type
    
    def _generate_generic_type_usage(
        self,
        type_obj: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
        current_library_name: Optional[str],
    ) -> UnifiedGraftModel:
        """
        Recursively generate nested type for generic type or argument (NOT wrapped in TYPE_USAGE).
        TYPE_USAGE is only the top-level entry point.
        """
        # Use the main type handler's internal method to generate nested type directly
        # (without TYPE_USAGE wrapper)
        type_handler = handlers.shared_handler.get(UnifiedGraftModelType.TYPE_USAGE)
        if type_handler and hasattr(type_handler, "_generate_unified_graft_model_for_type"):
            return type_handler._generate_unified_graft_model_for_type(
                type_obj, _parent_command, handlers, IsNullable.FALSE
            )
        # Fallback: create primitive type directly
        return UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE, []
        )
