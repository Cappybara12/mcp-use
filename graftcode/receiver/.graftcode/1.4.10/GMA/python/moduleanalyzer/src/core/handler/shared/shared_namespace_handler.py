from typing import Any

from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class SharedNamespaceHandler(AbstractHandler):
    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> Any:
        return analyzed_object
