"""Verify method/constructor handlers append COMMENT_DOC when documented."""

from __future__ import annotations

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.create_instance_analyzer_handler import (
    CreateInstanceAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_global_method_analyzer_handler import (
    GetGlobalMethodAnalyzerHandler,
)
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


class DocumentedService:
    """Service with documented members."""

    def __init__(self, name: str):
        """Create a service instance.

        Args:
            name (str): Display name for the service.
        """
        self.name = name

    def run(self, count: int) -> bool:
        """Run the service loop.

        Args:
            count (int): Iteration count.

        Returns:
            bool: True when the loop completes.
        """
        return count > 0

    @staticmethod
    def factory(label: str) -> "DocumentedService":
        """Build a service from a label.

        Args:
            label (str): Label applied to the new instance.

        Returns:
            DocumentedService: Configured instance.
        """
        return DocumentedService(label)


def global_helper(value: int) -> int:
    """Double the input.

    Args:
        value (int): Operand.

    Returns:
        int: Twice the operand.
    """
    return value * 2


def _comment_doc_in_payload(command: UnifiedGraftModel) -> UnifiedGraftModel | None:
    for item in command.get_payload():
        if (
            isinstance(item, UnifiedGraftModel)
            and item.graft_model_type == UnifiedGraftModelType.COMMENT_DOC
        ):
            return item
    return None


def test_invoke_instance_method_appends_comment_doc():
    handlers = Handlers()
    result = InvokeInstanceMethodAnalyzerHandler().generate_unified_graft_model(
        DocumentedService.run, None, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None
    assert result.get_payload()[-1] is doc


def test_invoke_static_method_appends_comment_doc():
    handlers = Handlers()
    result = InvokeStaticMethodAnalyzerHandler().generate_unified_graft_model(
        DocumentedService.factory, None, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None


def test_create_instance_appends_comment_doc():
    handlers = Handlers()
    parent = UnifiedGraftModel(
        "Python", UnifiedGraftModelType.TYPE_DEF, ["ns", "DocumentedService", 1]
    )
    result = CreateInstanceAnalyzerHandler().generate_unified_graft_model(
        DocumentedService.__init__, parent, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None
    summary = next(
        c
        for c in doc.get_payload()
        if isinstance(c, UnifiedGraftModel)
        and c.graft_model_type == UnifiedGraftModelType.COMMENT_SUMMARY
    )
    assert "Create a service instance" in summary.get_payload()[0]


def test_get_global_method_appends_comment_doc():
    handlers = Handlers()
    result = GetGlobalMethodAnalyzerHandler().generate_unified_graft_model(
        global_helper, None, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None


def test_get_type_appends_comment_doc():
    handlers = Handlers()
    result = GetTypeAnalyzerHandler().generate_unified_graft_model(
        DocumentedService, None, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None


def test_get_instance_field_appends_comment_doc_from_fget():
    handlers = Handlers()

    class PropertyAsField:
        def __init__(self, prop, prop_name: str):
            self.name = prop_name
            self.fget = getattr(prop, "fget", None)
            self.fset = getattr(prop, "fset", None)

    class HasLabel:
        @property
        def label(self) -> str:
            """Human-readable label."""
            return "x"

    field = PropertyAsField(HasLabel.label, "label")
    parent = UnifiedGraftModel(
        "Python", UnifiedGraftModelType.TYPE_DEF, ["ns", "DocumentedService"]
    )
    result = GetInstanceFieldAnalyzerHandler().generate_unified_graft_model(
        field, parent, handlers
    )
    doc = _comment_doc_in_payload(result)
    assert doc is not None
