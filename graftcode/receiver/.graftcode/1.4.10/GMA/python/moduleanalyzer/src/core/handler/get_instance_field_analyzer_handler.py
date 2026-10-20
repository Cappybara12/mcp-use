from typing import Any, get_type_hints

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.base_field_handler import BaseFieldHandler
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
)


class GetInstanceFieldAnalyzerHandler(BaseFieldHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for an instance field.

        :param analyzed_object: The field instance being analyzed.
        :param parent_command: The parent command containing context for the
                               analysis.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: A UnifiedGraftModel representing the instance field.
        """
        # Assume analyzed_object is an instance field
        instance_field = analyzed_object

        # Create a new model for the instance field
        get_instance_field_command = self.create_unified_graft_model(
            UnifiedGraftModelType.INSTANCE_FIELD
        )

        # Add the field name
        get_instance_field_command = self.add_field_name_to_payload(
            get_instance_field_command, instance_field, handlers
        )

        # Add the field type
        get_instance_field_command = self.add_field_type_to_payload(
            get_instance_field_command, instance_field, handlers
        )

        # Add the setter accessor
        get_instance_field_command = self.add_setter_to_payload(
            get_instance_field_command, instance_field, handlers
        )

        # Add the getter accessor
        get_instance_field_command = self.add_getter_to_payload(
            get_instance_field_command, instance_field, handlers
        )

        fget = getattr(instance_field, "fget", None)
        if fget is not None:
            get_instance_field_command = (
                SharedCommentDocHandler.append_to_payload_if_present(
                    fget, get_instance_field_command, handlers
                )
            )

        return get_instance_field_command

    def add_field_type_to_payload(
        self, command: UnifiedGraftModel, field: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the field type to the payload.

        :param command: The UnifiedGraftModel being built.
        :param field: The field being analyzed (may be a string name or an object).
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the field type added.
        """
        if hasattr(field, "fget") and field.fget:
            # Resolve postponed/string annotations first (e.g. "int"),
            # then fall back to raw __annotations__ if resolution fails.
            try:
                resolved_hints = get_type_hints(field.fget)
                return_annotation = resolved_hints.get("return")
            except Exception:
                annotations = getattr(field.fget, "__annotations__", {})
                return_annotation = annotations.get("return")
            if return_annotation is None:
                field_type = object
            elif isinstance(return_annotation, str):
                # Normalize common primitive annotation strings so they are not
                # treated as Python str instances by SharedTypeHandler.
                primitive_type_aliases = {
                    "int": int,
                    "str": str,
                    "bool": bool,
                    "float": float,
                    "bytes": bytes,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "object": object,
                }
                field_type = primitive_type_aliases.get(
                    return_annotation, return_annotation
                )
            else:
                # Keep actual type object (or typing object) so TYPE_USAGE can
                # resolve primitives/generics correctly.
                field_type = return_annotation
        # If field is a string (field name), we need to get the actual field value
        elif isinstance(field, str):
            # Get the class from the current_class attribute in the handler
            clazz = getattr(
                handlers.analyzer_handler.get(UnifiedGraftModelType.TYPE_DEF),
                "current_class",
                None,
            )
            if clazz and hasattr(clazz, field):
                # Get the field value to determine its type
                field_value = getattr(clazz, field)
                field_type = type(field_value)
            else:
                # Default to 'object' if we can't determine the type
                field_type = object
        else:
            # Use the type of the field object
            field_type = type(field)

        field_type_model = handlers.shared_handler.get(
            UnifiedGraftModelType.TYPE_USAGE
        ).generate_unified_graft_model(field_type, command, handlers)
        return command.add_arg_to_payload(field_type_model)

    def add_class_name_to_payload(
        self,
        command: UnifiedGraftModel,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Adds the class name to the payload.

        :param command: The UnifiedGraftModel being built.
        :param parent_command: The parent command containing context for the analysis.
        :param handlers: Handlers for generating parts of the UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the class name added.
        """
        class_name_model = handlers.shared_handler.get(
            UnifiedGraftModelType.CLASS_NAME
        ).generate_unified_graft_model(parent_command.payload[0], command, handlers)
        return command.add_arg_to_payload(class_name_model)
