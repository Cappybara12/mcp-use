from typing import Any, Optional, get_args, get_origin
from typing import Generic, TypeVar

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class SharedGenericParametersHandler(AbstractHandler):
    """
    Handler for generic type parameters of a class.
    
    Structure: GENERIC_PARAMETERS -> [TYPE_USAGE[]]
    Each TYPE_USAGE represents a generic parameter (e.g., T, K, V).
    """
    
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for generic type parameters.
        
        Structure matches spec:
        - GENERIC_PARAMETERS with payload: [TYPE_USAGE[]]
        
        :param analyzed_object: The class being analyzed.
        :param parent_command: The parent TYPE_DEF command.
        :param handlers: Handlers collection.
        :return: UnifiedGraftModel representing generic parameters.
        """
        generic_parameters = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GENERIC_PARAMETERS, []
        )
        
        # Extract generic parameters from the class
        # Check if class has __parameters__ attribute (Python 3.7+)
        if hasattr(analyzed_object, '__parameters__'):
            params = analyzed_object.__parameters__
            if params:
                # Use TYPE_USAGE handler which will delegate to TYPE_USAGE_GENERIC_ALIAS
                type_handler = handlers.shared_handler.get(
                    UnifiedGraftModelType.TYPE_USAGE
                )
                if type_handler:
                    for param in params:
                        # Generate TYPE_USAGE for each parameter (which wraps TYPE_USAGE_GENERIC_ALIAS)
                        type_usage = type_handler.generate_unified_graft_model(
                            param, parent_command, handlers
                        )
                        generic_parameters = generic_parameters.add_arg_to_payload(type_usage)
        
        return generic_parameters
