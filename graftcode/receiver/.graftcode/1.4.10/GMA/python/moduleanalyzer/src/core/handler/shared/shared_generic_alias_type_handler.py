from typing import Any, Optional

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


class SharedGenericAliasTypeHandler(SharedTypeHandler):
    """
    Handler for generic type parameters (type aliases like T, K, V).
    Matches netcore's SharedGenericAliasTypeHandler implementation.
    
    Structure: TYPE_USAGE → TYPE_USAGE_GENERIC_ALIAS → [IS_NULLABLE, ALIAS_NAME]
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for generic type aliases.
        
        Structure matches C#:
        - TYPE_USAGE wrapper
        - TYPE_USAGE_GENERIC_ALIAS with payload: [IS_NULLABLE, ALIAS_NAME]

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
            # Generic type parameters are typically not nullable unless explicitly constrained
            is_nullable = IsNullable.FALSE

        type_name = self.get_type_name(type_obj, current_library_name)

        # Create TYPE_USAGE_GENERIC_ALIAS with payload: [IS_NULLABLE, ALIAS_NAME]
        # Note: TYPE_USAGE wrapper is created by SharedTypeHandler, not here
        alias_type = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_GENERIC_ALIAS, []
        )
        alias_type = alias_type.add_arg_to_payload(is_nullable.value)
        alias_type = alias_type.add_arg_to_payload(type_name)  # ALIAS_NAME
        
        return alias_type
