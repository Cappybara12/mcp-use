from typing import Any

from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.base_field_handler import BaseFieldHandler


class GetGlobalFieldAnalyzerHandler(BaseFieldHandler):
    def generate_unified_graft_model(
        self, analyzed_object: Any, parent_command: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for a global field.

        :param analyzed_object: The global field being analyzed.
        :param parent_command: The parent command containing context for
            the analysis.
        :param handlers: Handlers for generating parts of the
            UnifiedGraftModel.
        :return: A UnifiedGraftModel representing the global field.
        """
        global_field = analyzed_object

        get_field_command = self.create_unified_graft_model(
            UnifiedGraftModelType.GLOBAL_FIELD
        )
        get_field_command = self.add_field_name_to_payload(
            get_field_command, global_field, handlers
        )
        get_field_command = self.add_field_type_to_payload(
            get_field_command, global_field, handlers
        )
        get_field_command = self.add_field_modifiers_to_payload(
            get_field_command, global_field, handlers
        )

        return get_field_command
