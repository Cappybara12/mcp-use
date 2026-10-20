from typing import Any, get_type_hints

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
)


class BaseMethodHandler(AbstractHandler):
    """
    Base class for method-related handlers that provides common functionality
    for adding method names, return types, and modifiers to UnifiedGraftModel
    payloads.

    This class reduces code duplication across various method handler classes.
    """

    @property
    def method_type(self) -> UnifiedGraftModelType:
        raise NotImplementedError

    def add_method_name_to_payload(
        self, command: UnifiedGraftModel, method: Any
    ) -> UnifiedGraftModel:
        """
        Adds the method name to the payload.

        :param command: The UnifiedGraftModel being built.
        :param method: The method being analyzed.
        :return: Updated UnifiedGraftModel with the method name added.
        """
        method_name = getattr(method, "__name__", getattr(method, "name", str(method)))
        return command.add_arg_to_payload(method_name)

    def add_return_type_to_payload(
        self, command: UnifiedGraftModel, method: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the return type to the payload.

        :param command: The UnifiedGraftModel being built.
        :param method: The method being analyzed.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the return type added.
        """
        # Resolve postponed/string annotations first (e.g. -> 'SimpleCar'),
        # then fall back to raw __annotations__ if resolution fails.
        # Raw string annotations would otherwise be classified as `str`
        # and generators would coerce complex results to string.
        try:
            return_annotation = get_type_hints(method).get("return")
        except Exception:
            return_annotation = getattr(method, "__annotations__", {}).get("return")

        if return_annotation is None:
            # Use NoneType directly instead of string "None" to get proper VOID mapping
            return_annotation = getattr(method, "return_type", type(None))

        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.TYPE_USAGE
            ).generate_unified_graft_model(
                (
                    return_annotation
                    if hasattr(method, "__annotations__")
                    else {"type": return_annotation}
                ),
                command,
                handlers,
            )
        )

    def add_modifiers_to_payload(
        self, command: UnifiedGraftModel, method: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds the method modifiers to the payload.

        :param command: The UnifiedGraftModel being built.
        :param method: The method being analyzed.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the method modifiers added.
        """
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.MODIFIER
            ).generate_unified_graft_model(method, command, handlers)
        )

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        analyzed_method = analyzed_object

        method_command = self.create_unified_graft_model(self.method_type)
        method_command = self.add_method_name_to_payload(method_command, analyzed_method)
        method_command = self.add_return_type_to_payload(
            method_command, analyzed_method, handlers
        )
        method_command = self.add_modifiers_to_payload(
            method_command, analyzed_method, handlers
        )
        method_command = self.add_parameters_to_payload(
            method_command, analyzed_method, handlers
        )

        return self.add_comment_doc_to_payload(
            analyzed_method, method_command, handlers
        )

    def add_parameters_to_payload(
        self, command: UnifiedGraftModel, method: Any, handlers: Any
    ) -> UnifiedGraftModel:
        """
        Adds method parameters to the payload.

        :param command: The UnifiedGraftModel being built.
        :param method: The method being analyzed.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: Updated UnifiedGraftModel with the parameters added.
        """
        return command.add_arg_to_payload(
            handlers.shared_handler.get(
                UnifiedGraftModelType.PARAMETERS_ARRAY
            ).generate_unified_graft_model(method, command, handlers)
        )

    def add_comment_doc_to_payload(
        self,
        analyzed_object: Any,
        command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """Append COMMENT_DOC when documentation is present (no-op otherwise)."""
        return SharedCommentDocHandler.append_to_payload_if_present(
            analyzed_object, command, handlers
        )
