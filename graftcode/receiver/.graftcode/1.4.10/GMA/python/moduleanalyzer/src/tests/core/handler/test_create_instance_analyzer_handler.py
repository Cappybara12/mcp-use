from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.create_instance_analyzer_handler import (
    CreateInstanceAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers


class SampleClass:
    def __init__(self, a, b):
        self.a = a
        self.b = b


class NoParamClass:
    def __init__(self):
        pass


def test_generate_unified_graft_model_with_parameters():
    handler = CreateInstanceAnalyzerHandler()
    handlers = Handlers()
    parent_command = UnifiedGraftModel(
        "Python",
        UnifiedGraftModelType.CLAZZ_INSTANCE,
        ["SampleClass", "SampleClass"],
    )

    result = handler.generate_unified_graft_model(
        SampleClass.__init__, parent_command, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.CONSTRUCTOR
    # Verify the structure has class name, modifier, and parameters
    assert len(result.payload) == 3
    # Class name is a string
    assert isinstance(result.payload[0], str)
    assert result.payload[0] == "SampleClass"
    # Modifier is an integer (ModifierType value)
    assert isinstance(result.payload[1], int)
    # Parameters array is a UnifiedGraftModel
    assert isinstance(result.payload[2], UnifiedGraftModel)
    assert result.payload[2].graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY


def test_generate_unified_graft_model_without_parameters():
    handler = CreateInstanceAnalyzerHandler()
    handlers = Handlers()
    parent_command = UnifiedGraftModel(
        "Python",
        UnifiedGraftModelType.CLAZZ_INSTANCE,
        ["NoParamClass", "NoParamClass"],
    )

    result = handler.generate_unified_graft_model(
        NoParamClass.__init__, parent_command, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.CONSTRUCTOR
    # Verify the structure has class name, modifier, and parameters array (even if empty)
    assert len(result.payload) == 3
    # Class name is a string
    assert isinstance(result.payload[0], str)
    assert result.payload[0] == "NoParamClass"
    # Modifier is an integer (ModifierType value)
    assert isinstance(result.payload[1], int)
    # Parameters array is still added (as a UnifiedGraftModel)
    assert isinstance(result.payload[2], UnifiedGraftModel)
    assert result.payload[2].graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY


def test_generate_unified_graft_model_with_empty_parent_command():
    handler = CreateInstanceAnalyzerHandler()
    handlers = Handlers()
    empty_parent_command = UnifiedGraftModel(
        "Python", UnifiedGraftModelType.CLAZZ_INSTANCE, []
    )

    result = handler.generate_unified_graft_model(
        SampleClass.__init__, empty_parent_command, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.CONSTRUCTOR
    # Verify the structure has class name (should be "UnnamedClass"), modifier, and parameters
    assert len(result.payload) == 3
    # Class name is a string (defaults to "UnnamedClass" when parent_command is empty)
    assert isinstance(result.payload[0], str)
    assert result.payload[0] == "UnnamedClass"
    # Modifier is an integer (ModifierType value)
    assert isinstance(result.payload[1], int)
    # Parameters array is a UnifiedGraftModel
    assert isinstance(result.payload[2], UnifiedGraftModel)
    assert result.payload[2].graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
