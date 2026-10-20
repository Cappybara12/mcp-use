from typing import Any

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.base_field_handler import BaseFieldHandler


class GetStaticFieldAnalyzerHandler(BaseFieldHandler):
    def generate_unified_graft_model(
        self, analyzed_object: Any, parent_command: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for analyzing static fields in a class.

        :param analyzed_object: The static field being analyzed.
        :param parent_command: The parent command containing context for the analysis.
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: A UnifiedGraftModel representing the static field.
        """
        # Create the UnifiedGraftModel for the static field
        get_static_field_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.STATIC_FIELD, []
        )

        # Add the field name to the payload
        get_static_field_command = self.add_field_name_to_payload(
            get_static_field_command, analyzed_object, handlers
        )

        # Add the field type to the payload
        get_static_field_command = self.add_field_type_to_payload(
            get_static_field_command, analyzed_object, handlers
        )

        # Add the setter accessor to the payload
        get_static_field_command = self.add_setter_to_payload(
            get_static_field_command, analyzed_object, handlers
        )

        # Add the getter accessor to the payload
        get_static_field_command = self.add_getter_to_payload(
            get_static_field_command, analyzed_object, handlers
        )

        return get_static_field_command

    def add_field_name_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field name to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed.
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field name added.
        """
        field_name_model = handlers.shared_handler.get(
            UnifiedGraftModelType.FIELD_NAME
        ).generate_unified_graft_model(field.__name__, command, handlers)
        return command.add_arg_to_payload(field_name_model)

    def add_field_type_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field type to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed.
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field type added.
        """
        field_type_model = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE
        ).generate_unified_graft_model(field, command, handlers)
        return command.add_arg_to_payload(field_type_model)

    def add_class_name_to_payload(
        self, command: UnifiedGraftModel, parent_command: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the class name to the payload.

        :param command: The UnifiedGraftModel being built.
        :param parent_command: The parent command containing context.
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the class name added.
        """
        class_name_model = handlers.shared_handler.get(
            UnifiedGraftModelType.CLASS_NAME
        ).generate_unified_graft_model(
            parent_command.get_payload()[0], command, handlers
        )
        return command.add_arg_to_payload(class_name_model)
