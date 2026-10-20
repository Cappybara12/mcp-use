from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType

from moduleanalyzer.src.core.handler.base_method_handler import BaseMethodHandler


class InvokeAbstractInstanceMethodAnalyzerHandler(BaseMethodHandler):
    @property
    def method_type(self) -> UnifiedGraftModelType:
        return UnifiedGraftModelType.ABSTRACT_INSTANCE_METHOD
