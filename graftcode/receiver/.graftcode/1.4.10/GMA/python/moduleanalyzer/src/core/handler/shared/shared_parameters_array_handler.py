import inspect
from typing import Any, Dict, Optional, get_type_hints

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class SharedParametersArrayHandler(AbstractHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: Optional[UnifiedGraftModel],
        handlers: Any,
    ) -> UnifiedGraftModel:
        parameter_array = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.PARAMETERS_ARRAY, []
        )
        return self._add_parameters_to_parameter_array(
            parameter_array, analyzed_object, handlers
        )

    def _add_parameters_to_parameter_array(
        self,
        parameter_array: UnifiedGraftModel,
        analyzed_object: Any,
        handlers: Any,
    ) -> UnifiedGraftModel:
        sig = inspect.signature(analyzed_object)
        type_hints = self._get_type_hints(analyzed_object)

        for name, param in sig.parameters.items():
            # Skip 'self' and 'cls' parameters - they are Python implementation details
            if name in ("self", "cls"):
                continue

            param_type = type_hints.get(param.name, "undefined")

            parameter_command = UnifiedGraftModel(
                RuntimeName.Python, UnifiedGraftModelType.PARAMETER, []
            )

            parameter_command = self._create_unified_graft_model_for_type_usage(
                handlers, param_type, parameter_array, parameter_command
            )
            parameter_command = self._create_unified_graft_model_for_argument_name(
                handlers, name, parameter_array, parameter_command
            )

            parameter_array = parameter_array.add_arg_to_payload(parameter_command)

        return parameter_array

    def _create_unified_graft_model_for_argument_name(
        self,
        handlers: Any,
        name: str,
        parameter_array: UnifiedGraftModel,
        parameter_command: UnifiedGraftModel,
    ) -> UnifiedGraftModel:
        argument_name_model = handlers.shared_handler.get(
            UnifiedGraftModelType.ARGUMENT_NAME
        ).generate_unified_graft_model(name, parameter_array, handlers)
        return parameter_command.add_arg_to_payload(argument_name_model)

    def _create_unified_graft_model_for_type_usage(
        self,
        handlers: Any,
        param_type: Any,
        parameter_array: UnifiedGraftModel,
        parameter_command: UnifiedGraftModel,
    ) -> UnifiedGraftModel:
        type_usage_model = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE
        ).generate_unified_graft_model(param_type, parameter_array, handlers)
        return parameter_command.add_arg_to_payload(type_usage_model)

    def _get_type_hints(self, analyzed_object: Any) -> Dict[str, Any]:
        """Helper function to get type hints for an analyzed object."""
        if hasattr(analyzed_object, "__annotations__"):
            return get_type_hints(analyzed_object)
        return {}
