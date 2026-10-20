"""GMA analyzes inheritance fixture and validates TYPE_INHERITANCE emission."""

from __future__ import annotations

from pathlib import Path

import pytest
from graftcode_protocol.enums.inheritance_kind import InheritanceKind
from graftcode_protocol.enums.type_kind import TypeKind
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.protocol.deserializers.unified_graft_model_deserializer import (
    UnifiedGraftModelDeserializer,
)

from moduleanalyzer.src.core.handler.module_analyzer_local import (
    PythonModuleAnalyzerLocal,
)

FIXTURE_DIR = Path(__file__).resolve().parents[4] / "test_fixtures" / "inheritance_test"


def _find_type_def(library, class_name: str):
    for item in library.get_payload():
        if (
            hasattr(item, "graft_model_type")
            and item.graft_model_type == UnifiedGraftModelType.TYPE_DEF
            and str(item.get_payload()[1]) == class_name
        ):
            return item
    raise AssertionError(f"TYPE_DEF not found: {class_name}")


@pytest.fixture
def analyzer() -> PythonModuleAnalyzerLocal:
    return PythonModuleAnalyzerLocal()


def test_analyze_local_emits_type_inheritance_for_child_class(analyzer: PythonModuleAnalyzerLocal) -> None:
    analyzed_bytes = analyzer.analyze_local(str(FIXTURE_DIR))
    library = UnifiedGraftModelDeserializer(analyzed_bytes, len(analyzed_bytes)).deserialize()
    child_class = _find_type_def(library, "ChildClass")

    inheritance = next(
        (
            item
            for item in child_class.get_payload()
            if hasattr(item, "graft_model_type")
            and item.graft_model_type == UnifiedGraftModelType.TYPE_INHERITANCE
        ),
        None,
    )
    assert inheritance is not None
    assert len(inheritance.get_payload()) >= 2

    kinds = [
        entry.get_payload()[0]
        for entry in inheritance.get_payload()
        if hasattr(entry, "graft_model_type")
        and entry.graft_model_type == UnifiedGraftModelType.TYPE_INHERITANCE_ENTRY
    ]
    assert InheritanceKind.BASE_CLASS in kinds
    assert InheritanceKind.INTERFACE in kinds


def test_analyze_local_emits_type_def_kind_interface_for_i_marker(
    analyzer: PythonModuleAnalyzerLocal,
) -> None:
    analyzed_bytes = analyzer.analyze_local(str(FIXTURE_DIR))
    library = UnifiedGraftModelDeserializer(analyzed_bytes, len(analyzed_bytes)).deserialize()
    i_marker = _find_type_def(library, "IMarker")

    type_def_kind = next(
        (
            item
            for item in i_marker.get_payload()
            if hasattr(item, "graft_model_type")
            and item.graft_model_type == UnifiedGraftModelType.TYPE_DEF_KIND
        ),
        None,
    )
    assert type_def_kind is not None
    assert type_def_kind.get_payload()[0] == TypeKind.INTERFACE


def test_analyze_local_imarker_has_no_type_inheritance(
    analyzer: PythonModuleAnalyzerLocal,
) -> None:
    analyzed_bytes = analyzer.analyze_local(str(FIXTURE_DIR))
    library = UnifiedGraftModelDeserializer(analyzed_bytes, len(analyzed_bytes)).deserialize()
    i_marker = _find_type_def(library, "IMarker")

    inheritance = next(
        (
            item
            for item in i_marker.get_payload()
            if hasattr(item, "graft_model_type")
            and item.graft_model_type == UnifiedGraftModelType.TYPE_INHERITANCE
        ),
        None,
    )
    assert inheritance is None
