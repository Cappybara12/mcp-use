from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.invoke_instance_method_analyzer_handler import (
    InvokeInstanceMethodAnalyzerHandler,
)


class SampleClass:
    def instance_method(self, a: int, b: str) -> bool:
        return True


def test_generate_unified_graft_model():
    handler = InvokeInstanceMethodAnalyzerHandler()
    handlers = Handlers()
    analyzed_method = SampleClass.instance_method

    result = handler.generate_unified_graft_model(analyzed_method, None, handlers)

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.INSTANCE_METHOD
    # Verify payload contains method name, return type, modifiers, and parameters
    assert len(result.payload) == 4
    # Method name should be in payload
    assert "instance_method" in result.payload
    # Should have modifier (int), parameters array (UnifiedGraftModel), and return type (UnifiedGraftModel)
    assert any(isinstance(item, int) for item in result.payload)
    assert any(
        isinstance(item, UnifiedGraftModel)
        and item.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
        for item in result.payload
    )
    assert any(
        isinstance(item, UnifiedGraftModel)
        and item.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
        for item in result.payload
    )


def test_add_method_name_to_payload():
    handler = InvokeInstanceMethodAnalyzerHandler()
    command = UnifiedGraftModel("Python", UnifiedGraftModelType.INSTANCE_METHOD, [])

    result = handler.add_method_name_to_payload(command, SampleClass.instance_method)

    assert isinstance(result, UnifiedGraftModel)
    assert "instance_method" in result.payload


def test_add_return_type_to_payload():
    handler = InvokeInstanceMethodAnalyzerHandler()
    handlers = Handlers()
    command = UnifiedGraftModel("Python", UnifiedGraftModelType.INSTANCE_METHOD, [])

    result = handler.add_return_type_to_payload(
        command, SampleClass.instance_method, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    # Should have added a return type (UnifiedGraftModel with TYPE_USAGE)
    assert len(result.payload) == 1
    assert isinstance(result.payload[0], UnifiedGraftModel)
    assert result.payload[0].graft_model_type == UnifiedGraftModelType.TYPE_USAGE


def test_add_modifiers_to_payload():
    handler = InvokeInstanceMethodAnalyzerHandler()
    handlers = Handlers()
    command = UnifiedGraftModel("Python", UnifiedGraftModelType.INSTANCE_METHOD, [])

    result = handler.add_modifiers_to_payload(
        command, SampleClass.instance_method, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    # Should have added a modifier (int value)
    assert len(result.payload) == 1
    assert isinstance(result.payload[0], int)
