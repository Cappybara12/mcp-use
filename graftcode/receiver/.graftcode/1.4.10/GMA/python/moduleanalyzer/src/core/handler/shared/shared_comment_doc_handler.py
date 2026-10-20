"""Build a COMMENT_DOC subtree from a Python docstring on a callable.

Reads ``__doc__`` directly (never ``inspect.getdoc``) so constructors do not
inherit documentation from ``object.__init__`` via the MRO.

Parses Google / NumPy / reST docstrings through ``docstring_parser`` and maps
sections onto the neutral CommentDoc UGM wire contract shared with other GMA
runtimes and GCG.

``COMMENT_SOURCE`` payload field ``file`` (index 1) is the source filename only,
not an absolute path.
"""

from __future__ import annotations

from types import FunctionType
from typing import Any, List, Optional

from docstring_parser import parse as parse_docstring
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)
from moduleanalyzer.src.utils.analyzer_config import should_emit_code_examples


def _read_docstring(analyzed_object: Any) -> Optional[str]:
    doc = getattr(analyzed_object, "__doc__", None)
    if doc is None:
        return None
    text = str(doc).strip()
    return text if text else None


class SharedCommentDocHandler:
    """Maps a Python docstring to a structured COMMENT_DOC UGM subtree."""

    @staticmethod
    def append_to_payload_if_present(
        analyzed_object: Any,
        command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        handler = handlers.shared_handler.get(UnifiedGraftModelType.COMMENT_DOC)
        if not isinstance(handler, SharedCommentDocHandler):
            return command
        return handler.append_to_payload(analyzed_object, command, handlers)

    def append_to_payload(
        self,
        analyzed_object: Any,
        command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        try:
            node = self.generate_unified_graft_model(analyzed_object, command, handlers)
        except Exception:
            return command
        if node is None:
            return command
        return command.add_arg_to_payload(node)

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        _parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> Optional[UnifiedGraftModel]:
        if not callable(analyzed_object) and not isinstance(
            analyzed_object, (FunctionType, type)
        ):
            return None

        raw_doc = _read_docstring(analyzed_object)
        if raw_doc is None:
            return None

        parsed = parse_docstring(raw_doc)
        context = CommentDocBuildContext(
            analyzed_object=analyzed_object,
            raw_doc=raw_doc,
            parsed=parsed,
            emit_code_examples=should_emit_code_examples(),
        )

        children: List[UnifiedGraftModel] = []
        for section_handler in handlers.comment_doc_section_handlers:
            node = section_handler.build_section(context)
            if node is not None:
                children.append(node)

        if not children:
            return None

        return ugm_node(UnifiedGraftModelType.COMMENT_DOC, children)
