from __future__ import annotations

import inspect
from typing import Any, Optional

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_style import (
    comment_style,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    COMMENT_LANGUAGE,
    normalize_source_file_name,
    ugm_node,
)


class CommentSourceSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        return _build_source(
            context.analyzed_object,
            context.raw_doc,
            context.emit_code_examples,
            context.parsed.style,
        )


def _build_source(
    analyzed_object: Any,
    raw_doc: str,
    emit_code: bool,
    style: Any,
) -> Optional[UnifiedGraftModel]:
    file_path = ""
    line_start = 0
    line_end = 0
    try:
        file_path = inspect.getsourcefile(analyzed_object) or ""
        lines, start = inspect.getsourcelines(analyzed_object)
        line_start = start
        line_end = start + len(lines) - 1
    except (OSError, TypeError, ValueError):
        pass

    raw_source = raw_doc if emit_code else ""
    if not file_path and not line_start and not raw_source:
        return None

    return ugm_node(
        UnifiedGraftModelType.COMMENT_SOURCE,
        [
            COMMENT_LANGUAGE,
            normalize_source_file_name(file_path),
            line_start,
            line_end,
            comment_style(style),
            raw_source,
        ],
    )
