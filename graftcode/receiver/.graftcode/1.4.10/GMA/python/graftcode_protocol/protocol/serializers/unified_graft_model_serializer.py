from __future__ import annotations

import io

from graftcode_protocol.protocol.serializers.type_serializer import TypeSerializer
from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.models.unified_graft_model import (
    UnifiedGraftModel,
)


class UnifiedGraftModelSerializer:
    def serialize(self, root_command: UnifiedGraftModel) -> bytes:
        ms = io.BytesIO()

        ms.write(bytes([root_command.runtime_name.value, 0]))

        ms.write(bytes([0, 0, 0, 0, 0, 0, 0]))

        # Write the platform/runtime indicator and command type.
        ms.write(bytes([RuntimeName.Python.value, root_command.graft_model_type.value]))

        self.serialize_recursively(root_command, ms)
        return ms.getvalue()

    def serialize_recursively(self, command: UnifiedGraftModel, ms: io.BytesIO) -> None:
        for item in command.get_payload():
            if isinstance(item, UnifiedGraftModel):
                ms.write(bytes(TypeSerializer.serialize_command(item)))
                self.serialize_recursively(item, ms)
            else:
                ms.write(bytes(TypeSerializer.serialize_primitive(item)))
