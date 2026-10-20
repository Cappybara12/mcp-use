"""CommentDoc integration tests against grft-test-simple-car fixtures."""

from __future__ import annotations

from pathlib import Path
import sys

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
import pytest

from moduleanalyzer.src.core.handler.get_instance_field_analyzer_handler import (
    GetInstanceFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_type_analyzer_handler import (
    GetTypeAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.invoke_instance_method_analyzer_handler import (
    InvokeInstanceMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.invoke_static_method_analyzer_handler import (
    InvokeStaticMethodAnalyzerHandler,
)


def _simple_car_package_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = (
            parent
            / "graftcode-e2e-tests"
            / "e2e-test-packages"
            / "src"
            / "python"
            / "grft-test-simple-car"
        )
        if candidate.is_dir():
            return candidate
    pytest.skip("grft-test-simple-car fixture not available")


@pytest.fixture(scope="module")
def simple_car_types():
    root = _simple_car_package_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from grft_test_simple_car.simple_car import SimpleCar
    from grft_test_simple_car.vehicle import Vehicle

    return SimpleCar, Vehicle


def _find_child(
    root: UnifiedGraftModel, graft_type: UnifiedGraftModelType
) -> UnifiedGraftModel | None:
    for item in root.get_payload():
        if isinstance(item, UnifiedGraftModel) and item.graft_model_type == graft_type:
            return item
    return None


def _find_comment_doc(node: UnifiedGraftModel) -> UnifiedGraftModel | None:
    return _find_child(node, UnifiedGraftModelType.COMMENT_DOC)


def _find_instance_field(
    type_def: UnifiedGraftModel, field_name: str
) -> UnifiedGraftModel:
    for item in type_def.get_payload():
        if (
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.INSTANCE_FIELD
            and item.get_payload()[0] == field_name
        ):
            return item
    raise AssertionError(f"INSTANCE_FIELD {field_name!r} not found")


def test_simple_car_class_has_comment_doc(simple_car_types):
    simple_car, _ = simple_car_types
    handlers = Handlers()
    type_def = GetTypeAnalyzerHandler().generate_unified_graft_model(
        simple_car, None, handlers
    )
    doc = _find_comment_doc(type_def)
    assert doc is not None
    summary = _find_child(doc, UnifiedGraftModelType.COMMENT_SUMMARY)
    assert summary is not None
    assert "string identifier" in summary.get_payload()[0]
    links = _find_child(doc, UnifiedGraftModelType.COMMENT_LINKS_ARRAY)
    assert links is not None


def test_simple_car_property_has_comment_doc(simple_car_types):
    simple_car, _ = simple_car_types
    handlers = Handlers()
    type_def = GetTypeAnalyzerHandler().generate_unified_graft_model(
        simple_car, None, handlers
    )
    id_field = _find_instance_field(type_def, "id")
    doc = _find_comment_doc(id_field)
    assert doc is not None
    summary = _find_child(doc, UnifiedGraftModelType.COMMENT_SUMMARY)
    assert summary is not None
    assert "identifier" in summary.get_payload()[0].lower()


def test_create_default_has_examples(simple_car_types):
    simple_car, _ = simple_car_types
    handlers = Handlers()
    result = InvokeStaticMethodAnalyzerHandler().generate_unified_graft_model(
        simple_car.create_default, None, handlers
    )
    doc = _find_comment_doc(result)
    assert doc is not None
    examples = _find_child(doc, UnifiedGraftModelType.COMMENT_EXAMPLES_ARRAY)
    assert examples is not None


def test_get_total_cars_created_has_metadata(simple_car_types):
    simple_car, _ = simple_car_types
    handlers = Handlers()
    result = InvokeStaticMethodAnalyzerHandler().generate_unified_graft_model(
        simple_car.get_total_cars_created, None, handlers
    )
    doc = _find_comment_doc(result)
    assert doc is not None
    metadata = _find_child(doc, UnifiedGraftModelType.COMMENT_METADATA)
    assert metadata is not None
    assert metadata.get_payload()[0] == "graftcode"


def test_get_tags_has_deprecated_and_array_return(simple_car_types):
    simple_car, _ = simple_car_types
    handlers = Handlers()
    result = InvokeInstanceMethodAnalyzerHandler().generate_unified_graft_model(
        simple_car.get_tags, None, handlers
    )
    doc = _find_comment_doc(result)
    assert doc is not None
    deprecated = _find_child(doc, UnifiedGraftModelType.COMMENT_DEPRECATED)
    assert deprecated is not None
    assert "Since 0.2.0" in deprecated.get_payload()[1]
    returns = _find_child(doc, UnifiedGraftModelType.COMMENT_RETURNS)
    assert returns is not None
    assert returns.get_payload()[1] == "array"


def test_vehicle_property_field_analyzer_wires_fget_doc(simple_car_types):
    _, vehicle = simple_car_types
    handlers = Handlers()

    class PropertyAsField:
        def __init__(self, prop, prop_name: str):
            self.name = prop_name
            self.fget = getattr(prop, "fget", None)
            self.fset = getattr(prop, "fset", None)

    field = PropertyAsField(vehicle.id, "id")
    parent = UnifiedGraftModel(
        "Python", UnifiedGraftModelType.TYPE_DEF, ["ns", "Vehicle"]
    )
    result = GetInstanceFieldAnalyzerHandler().generate_unified_graft_model(
        field, parent, handlers
    )
    doc = _find_comment_doc(result)
    assert doc is not None
