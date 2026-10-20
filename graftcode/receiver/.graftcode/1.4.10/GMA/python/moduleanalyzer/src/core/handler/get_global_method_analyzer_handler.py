import inspect
from typing import Any

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.base_method_handler import BaseMethodHandler


class GetGlobalMethodAnalyzerHandler(BaseMethodHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for a global method.

        :param analyzed_object: The global method being analyzed.
        :param parent_command: The parent command containing context for the
                               analysis.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: A UnifiedGraftModel representing the global method.
        """
        analyzed_method = analyzed_object

        global_method_command = self.create_unified_graft_model(
            UnifiedGraftModelType.GLOBAL_METHOD
        )
        global_method_command = self.add_method_name_to_payload(
            global_method_command, analyzed_method
        )
        global_method_command = self.add_return_type_to_payload(
            global_method_command, analyzed_method, handlers
        )
        global_method_command = self.add_modifiers_to_payload(
            global_method_command, analyzed_method, handlers
        )

        # Check if the method should have parameters added
        should_add_parameters = False

        # First, check if there's a custom 'params' attribute
        if hasattr(analyzed_method, "params"):
            params_attr = getattr(analyzed_method, "params")
            # Only add parameters if params is a non-empty list
            should_add_parameters = (
                isinstance(params_attr, list) and len(params_attr) > 0
            )
        elif callable(analyzed_method):
            # If no custom params attribute, use inspect.signature
            try:
                sig = inspect.signature(analyzed_method)
                should_add_parameters = len(sig.parameters) > 0
            except (ValueError, TypeError):
                # Cannot get signature for some built-in functions
                pass

        if should_add_parameters:
            global_method_command = self.add_parameters_to_payload(
                global_method_command, analyzed_method, handlers
            )

        return self.add_comment_doc_to_payload(
            analyzed_method, global_method_command, handlers
        )
