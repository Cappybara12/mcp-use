from typing import Any, Optional

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class SharedVoidTypeHandler:
    """
    Handler for void types.
    Matches netcore's SharedVoidTypeHandler implementation.
    
    Structure: TYPE_USAGE → TYPE_USAGE_VOID → []
    """

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for void types.
        
        Structure matches C#:
        - TYPE_USAGE wrapper
        - TYPE_USAGE_VOID with empty payload

        :param analyzed_object: The object being analyzed.
        :param _parent_command: The parent command related to the object (unused, can be None).
        :param handlers: A collection of handlers (unused for void).
        :return: A UnifiedGraftModel instance representing void type.
        """
        # Create TYPE_USAGE_VOID directly (TYPE_USAGE wrapper is created by SharedTypeHandler)
        return UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.TYPE_USAGE_VOID, []
        )
