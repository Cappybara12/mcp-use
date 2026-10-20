from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType

from moduleanalyzer.src.core.handler.base_method_handler import BaseMethodHandler


class InvokeInstanceMethodAnalyzerHandler(BaseMethodHandler):
    """Handler for analyzing instance methods and generating graft models."""

    @property
    def method_type(self) -> UnifiedGraftModelType:
        return UnifiedGraftModelType.INSTANCE_METHOD
