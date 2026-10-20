import inspect
from typing import Any

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
)


class CreateInstanceAnalyzerHandler(AbstractHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for creating an instance of a class in
        the Python runtime.

        :param analyzed_object: The constructor or class being analyzed.
        :param parent_command: The parent command containing context for the
                               analysis.
        :param handlers: Handlers for generating parts of the
                         UnifiedGraftModel.
        :return: A UnifiedGraftModel representing the create instance command.
        """
        # Create a UnifiedGraftModel for the CONSTRUCTOR type
        create_instance_command = self.create_unified_graft_model(
            UnifiedGraftModelType.CONSTRUCTOR
        )

        # Add the class name to the payload
        # payload[0] is namespace, payload[1] is class name (matches .NET Core structure)
        payload = parent_command.get_payload()
        class_name = payload[1] if payload and len(payload) > 1 else "UnnamedClass"
        create_instance_command = create_instance_command.add_arg_to_payload(
            handlers.shared_handler[
                UnifiedGraftModelType.CLASS_NAME
            ].generate_unified_graft_model(
                class_name, create_instance_command, handlers
            )
        )

        # Add modifiers to the payload using the appropriate handler
        create_instance_command = create_instance_command.add_arg_to_payload(
            handlers.shared_handler[
                UnifiedGraftModelType.MODIFIER
            ].generate_unified_graft_model(
                analyzed_object, create_instance_command, handlers
            )
        )

        # Optionally add parameters if the analyzed object has any
        if inspect.signature(analyzed_object).parameters:
            create_instance_command = create_instance_command.add_arg_to_payload(
                handlers.shared_handler[
                    UnifiedGraftModelType.PARAMETERS_ARRAY
                ].generate_unified_graft_model(
                    analyzed_object,
                    create_instance_command,
                    handlers,
                )
            )

        return SharedCommentDocHandler.append_to_payload_if_present(
            analyzed_object, create_instance_command, handlers
        )
