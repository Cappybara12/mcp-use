from __future__ import annotations

import json

from graftcode_protocol.protocol.deserializers.unified_graft_model_deserializer import (
    UnifiedGraftModelDeserializer,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel


class _UnifiedGraftModelEncoder(json.JSONEncoder):
    """Custom JSON encoder that knows how to serialize UnifiedGraftModel."""

    def default(self, obj):
        if isinstance(obj, UnifiedGraftModel):
            return {
                "runtimeName": obj.runtime_name.name,
                "unifiedGraftModelType": obj.graft_model_type.name,
                "payload": obj.payload,
            }
        return super().default(obj)


class UnifiedGraftModelToJsonSerializer:
    @staticmethod
    def serialize(model: UnifiedGraftModel) -> str:
        """Serialize a UnifiedGraftModel to JSON string."""
        return json.dumps(model, cls=_UnifiedGraftModelEncoder, separators=(",", ": "))

    @staticmethod
    def serialize_from_byte_array(byte_array: bytes) -> str:
        """Deserialize from byte array and then serialize to JSON string."""
        deserializer = UnifiedGraftModelDeserializer(byte_array)
        unified_graft_model = deserializer.deserialize()
        return UnifiedGraftModelToJsonSerializer.serialize(unified_graft_model)
