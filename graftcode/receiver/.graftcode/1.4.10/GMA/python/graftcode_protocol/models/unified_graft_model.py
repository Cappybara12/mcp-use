from __future__ import annotations

from typing import Any, List, Optional

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)


class UnifiedGraftModel:
    """Unified model representing a graft command/operation."""

    def __init__(
        self,
        runtime_name: RuntimeName,
        graft_model_type: UnifiedGraftModelType,
        payload: List[Any],
    ) -> None:
        self.runtime_name = runtime_name
        self.graft_model_type = graft_model_type
        self.payload = payload

    def get_payload(self) -> List[Any]:
        return self.payload

    def get_payload_size(self) -> int:
        return len(self.payload)

    @staticmethod
    def create_response(
        response: Any, runtime_name: RuntimeName
    ) -> "UnifiedGraftModel":
        return UnifiedGraftModel(runtime_name, UnifiedGraftModelType.OUT, [response])

    @staticmethod
    def create_reference(guid: Any, runtime_name: RuntimeName) -> "UnifiedGraftModel":
        return UnifiedGraftModel(runtime_name, UnifiedGraftModelType.REF, [guid])

    @staticmethod
    def create_array_response(
        array: List[Any], runtime_name: RuntimeName
    ) -> "UnifiedGraftModel":
        return UnifiedGraftModel(runtime_name, UnifiedGraftModelType.ARRAY, array)

    def drop_first_payload_argument(self) -> "UnifiedGraftModel":
        payload_args = []
        payload_args.extend(self.payload)
        if len(payload_args) != 0:
            payload_args.pop(0)
        return UnifiedGraftModel(self.runtime_name, self.graft_model_type, payload_args)

    def add_arg_to_payload(self, argument: Any) -> "UnifiedGraftModel":
        merged_payload = self.payload + [argument]
        return UnifiedGraftModel(
            self.runtime_name, self.graft_model_type, merged_payload
        )

    def prepend_arg_to_payload(
        self, current_command: Optional["UnifiedGraftModel"]
    ) -> "UnifiedGraftModel":
        if current_command is None:
            return UnifiedGraftModel(
                self.runtime_name, self.graft_model_type, self.payload
            )
        else:
            return UnifiedGraftModel(
                self.runtime_name,
                self.graft_model_type,
                [current_command] + self.payload,
            )

    def to_string(self) -> str:
        return (
            "Target runtime: "
            + str(self.runtime_name)
            + " Command type: "
            + str(self.graft_model_type)
            + " Payload: "
            + str(self.payload)
        )

    def __eq__(self, element: object) -> bool:
        self.is_equal = False
        if self is element:
            self.is_equal = True
        if element is None or self.__class__ != element.__class__:
            self.is_equal = False
        if (
            self.graft_model_type is element.graft_model_type
            and self.runtime_name is element.runtime_name
        ):
            self.is_equal = True
        len(self.payload)
        len(element.payload)
        if len(self.payload) == len(element.payload):
            i = 0
            array_item_equal = False
            for payload_item in self.payload:
                if payload_item.__eq__(element.payload[i]):
                    array_item_equal = True
                else:
                    array_item_equal = False
                i += 1
            self.is_equal = array_item_equal
        else:
            self.is_equal = False
        return self.is_equal

    def __hash__(self) -> int:
        """Make the object hashable."""
        return hash(
            (
                self.runtime_name,
                self.graft_model_type,
                (
                    tuple(self.payload)
                    if isinstance(self.payload, list)
                    else self.payload
                ),
            )
        )

    def get_unified_graft_model_type(self) -> UnifiedGraftModelType:
        return self.graft_model_type
