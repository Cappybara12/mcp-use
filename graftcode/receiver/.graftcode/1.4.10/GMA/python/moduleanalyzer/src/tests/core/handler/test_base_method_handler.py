"""
Tests for BaseMethodHandler.add_return_type_to_payload.

Focus: string (forward-reference) return annotations such as
`def duplicate(self) -> 'SimpleCar':` must resolve to the actual class
instead of being classified as the Python `str` primitive.
"""

from graftcode_protocol.enums.graft_code_primitive_type import GraftCodePrimitiveType
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.invoke_instance_method_analyzer_handler import (
    InvokeInstanceMethodAnalyzerHandler,
)


class ForwardRefCar:
    """Class whose methods return itself via quoted forward references."""

    def duplicate(self) -> "ForwardRefCar":
        return self

    def quoted_primitive(self) -> "int":
        return 0

    def plain_string(self) -> str:
        return ""

    def returns_none(self) -> None:
        return None

    def no_annotation(self):
        return None


def _generate_return_type_usage(method) -> UnifiedGraftModel:
    handler = InvokeInstanceMethodAnalyzerHandler()
    handlers = Handlers()
    command = UnifiedGraftModel("Python", UnifiedGraftModelType.INSTANCE_METHOD, [])

    result = handler.add_return_type_to_payload(command, method, handlers)

    assert len(result.payload) == 1
    type_usage = result.payload[0]
    assert isinstance(type_usage, UnifiedGraftModel)
    assert type_usage.graft_model_type == UnifiedGraftModelType.TYPE_USAGE
    return type_usage.payload[0]


def test_forward_ref_return_resolves_to_class():
    node = _generate_return_type_usage(ForwardRefCar.duplicate)

    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    # Payload: [IS_NULLABLE, NAMESPACE, TYPENAME, PRIMITIVE_TYPE, ASSEMBLY_NAME, ASSEMBLY_VERSION]
    assert node.payload[2] == "ForwardRefCar"
    assert node.payload[3] == GraftCodePrimitiveType.GRAFT_MODEL.value


def test_quoted_primitive_return_resolves_to_primitive():
    node = _generate_return_type_usage(ForwardRefCar.quoted_primitive)

    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert node.payload[2] == "int"
    assert node.payload[3] == GraftCodePrimitiveType.INTEGER.value


def test_plain_string_return_still_maps_to_string():
    node = _generate_return_type_usage(ForwardRefCar.plain_string)

    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert node.payload[2] == "str"
    assert node.payload[3] == GraftCodePrimitiveType.STRING.value


def test_none_return_maps_to_void():
    node = _generate_return_type_usage(ForwardRefCar.returns_none)

    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_VOID


def test_missing_annotation_maps_to_void():
    node = _generate_return_type_usage(ForwardRefCar.no_annotation)

    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_VOID


def test_unresolvable_forward_ref_falls_back_without_error():
    def method_with_bad_annotation(self):
        return None

    # Simulate an annotation referencing a name that cannot be resolved.
    method_with_bad_annotation.__annotations__["return"] = "NotARealClass123"

    node = _generate_return_type_usage(method_with_bad_annotation)

    # Falls back to legacy behaviour (raw string analyzed as str instance);
    # the important part is that analysis does not raise.
    assert node.graft_model_type == UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE
    assert node.payload[3] == GraftCodePrimitiveType.STRING.value
