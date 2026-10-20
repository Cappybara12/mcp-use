from typing import Any

from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class SharedFieldNameHandler(AbstractHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> str:
        # analyzed_object is already a string (field name), return it directly
        if isinstance(analyzed_object, str):
            return analyzed_object
        # Fallback for objects with name attribute
        return getattr(analyzed_object, "name", str(analyzed_object))
