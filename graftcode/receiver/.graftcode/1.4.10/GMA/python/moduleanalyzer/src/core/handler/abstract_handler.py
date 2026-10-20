from abc import ABC, abstractmethod
from typing import Any

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class AbstractHandler(ABC):
    """
    Abstract base class for handlers that generate a UnifiedGraftModel.

    Subclasses must implement the `generate_unified_graft_model` method to
    define how the graft model is generated based on the analyzed object.
    """

    @abstractmethod
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,  # Handlers class - avoiding circular import
    ) -> UnifiedGraftModel:
        """
        Abstract method to generate a UnifiedGraftModel based on the
        analyzed object.

        Args:
            analyzed_object: The object being analyzed, which provides the
                             data for the graft model.
            parent_command: The parent UnifiedGraftModel, if applicable, to
                            which this model is related.
            handlers: A collection of handlers that might be used in
                      generating the graft model.

        Returns:
            A UnifiedGraftModel instance representing the analyzed object.
        """
        pass

    def create_unified_graft_model(
        self, graft_model_type: UnifiedGraftModelType
    ) -> UnifiedGraftModel:
        """
        Creates a new UnifiedGraftModel with the given type and an empty
        payload.

        Args:
            graft_model_type: The type of the UnifiedGraftModel to create.

        Returns:
            A new UnifiedGraftModel instance with the specified type and an
            empty payload.
        """
        return UnifiedGraftModel(RuntimeName.Python, graft_model_type, [])
