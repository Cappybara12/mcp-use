from typing import Any

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class BaseFieldHandler(AbstractHandler):
    """
    Base class for field-related handlers that provides common functionality
    for adding field names, types, and modifiers to UnifiedGraftModel payloads.

    This class reduces code duplication across various field handler classes.
    """

    def add_field_name_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field name to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed (may be a string name or an object).
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field name added.
        """
        # Check if field is already a string (field name)
        if isinstance(field, str):
            field_name = field
        else:
            # Otherwise try to get the name attribute
            field_name = getattr(field, "__name__", getattr(field, "name", str(field)))

        field_name_model = handlers.shared_handler.get(
            UnifiedGraftModelType.FIELD_NAME
        ).generate_unified_graft_model(field_name, command, handlers)
        return command.add_arg_to_payload(field_name_model)

    def add_field_type_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field type to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field type added.
        """
        field_type = type(field).__name__
        field_type_model = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE
        ).generate_unified_graft_model(field_type, command, handlers)
        return command.add_arg_to_payload(field_type_model)

    def add_field_modifiers_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field modifiers to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field modifiers added.
        """
        modifier_type_model = handlers.shared_handler.get(
            UnifiedGraftModelType.MODIFIER
        ).generate_unified_graft_model(field, command, handlers)
        return command.add_arg_to_payload(modifier_type_model)

    def add_setter_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        setter_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.SETTER, []
        )
        if hasattr(field, "fset"):
            from graftcode_protocol.enums.modifier_type import ModifierType

            if field.fset:
                setter_modifier = handlers.shared_handler.get(
                    UnifiedGraftModelType.MODIFIER
                ).generate_unified_graft_model(field.fset, setter_command, handlers)
            else:
                setter_modifier = ModifierType.PRIVATE.value
        else:
            setter_modifier = handlers.shared_handler.get(
                UnifiedGraftModelType.MODIFIER
            ).generate_unified_graft_model(field, setter_command, handlers)
        setter_command = setter_command.add_arg_to_payload(setter_modifier)
        return command.add_arg_to_payload(setter_command)

    def add_getter_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        getter_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GETTER, []
        )
        if hasattr(field, "fget") and field.fget:
            getter_modifier = handlers.shared_handler.get(
                UnifiedGraftModelType.MODIFIER
            ).generate_unified_graft_model(field.fget, getter_command, handlers)
        else:
            getter_modifier = handlers.shared_handler.get(
                UnifiedGraftModelType.MODIFIER
            ).generate_unified_graft_model(field, getter_command, handlers)
        getter_command = getter_command.add_arg_to_payload(getter_modifier)
        return command.add_arg_to_payload(getter_command)
