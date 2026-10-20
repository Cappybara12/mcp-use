from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.shared.shared_parameters_array_handler import (
    SharedParametersArrayHandler,
)


def sample_function(a: int, b: str):
    return f"{a} and {b}"


class SampleClass:
    def instance_method(self, x: int, y: str) -> str:
        return f"{x} and {y}"

    @classmethod
    def class_method(cls, x: int, y: str) -> str:
        return f"{x} and {y}"

    @staticmethod
    def static_method(x: int, y: str) -> str:
        return f"{x} and {y}"


def method_with_self_named_param(self_data: dict, other: str) -> str:
    """Function with a parameter that starts with 'self' but isn't 'self'."""
    return f"{self_data} and {other}"


def test_generate_unified_graft_model():
    handler = SharedParametersArrayHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(sample_function, None, handlers)

    assert isinstance(result, UnifiedGraftModel)
    assert result.runtime_name == RuntimeName.Python
    assert result.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
    assert len(result.payload) == 2

    param1, param2 = result.payload

    # First parameter (a: int)
    assert isinstance(param1, UnifiedGraftModel)
    assert param1.runtime_name == RuntimeName.Python
    assert param1.graft_model_type == UnifiedGraftModelType.PARAMETER
    assert len(param1.payload) == 2
    # First element is the type (UnifiedGraftModel for TYPE_USAGE)
    assert isinstance(param1.payload[0], UnifiedGraftModel)
    assert param1.payload[0].graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    # Second element is the argument name (string)
    assert param1.payload[1] == "a"

    # Second parameter (b: str)
    assert isinstance(param2, UnifiedGraftModel)
    assert param2.runtime_name == RuntimeName.Python
    assert param2.graft_model_type == UnifiedGraftModelType.PARAMETER
    assert len(param2.payload) == 2
    # First element is the type (UnifiedGraftModel for TYPE_USAGE)
    assert isinstance(param2.payload[0], UnifiedGraftModel)
    assert param2.payload[0].graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    # Second element is the argument name (string)
    assert param2.payload[1] == "b"


def test_instance_method_excludes_self_parameter():
    """Test that 'self' parameter is excluded from instance methods."""
    handler = SharedParametersArrayHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        SampleClass.instance_method, None, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
    # Should only have 2 parameters (x and y), not 3 (self, x, y)
    assert len(result.payload) == 2

    param_names = [param.payload[1] for param in result.payload]
    assert "self" not in param_names
    assert "x" in param_names
    assert "y" in param_names


def test_class_method_excludes_cls_parameter():
    """Test that 'cls' parameter is excluded from class methods."""
    handler = SharedParametersArrayHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        SampleClass.class_method, None, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
    # Should only have 2 parameters (x and y), not 3 (cls, x, y)
    assert len(result.payload) == 2

    param_names = [param.payload[1] for param in result.payload]
    assert "cls" not in param_names
    assert "x" in param_names
    assert "y" in param_names


def test_static_method_has_all_parameters():
    """Test that static methods retain all parameters (no self/cls)."""
    handler = SharedParametersArrayHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        SampleClass.static_method, None, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
    # Should have all 2 parameters (x and y)
    assert len(result.payload) == 2

    param_names = [param.payload[1] for param in result.payload]
    assert "x" in param_names
    assert "y" in param_names


def test_self_prefix_parameter_not_excluded():
    """Test that parameters starting with 'self' but not exactly 'self' are kept."""
    handler = SharedParametersArrayHandler()
    handlers = Handlers()

    result = handler.generate_unified_graft_model(
        method_with_self_named_param, None, handlers
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.PARAMETERS_ARRAY
    # Should have both parameters (self_data and other)
    assert len(result.payload) == 2

    param_names = [param.payload[1] for param in result.payload]
    assert "self_data" in param_names
    assert "other" in param_names
