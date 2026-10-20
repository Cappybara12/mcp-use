from __future__ import annotations

from typing import List, Optional

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    COMMENT_LANGUAGE,
    ugm_node,
)


class CommentExamplesSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        nodes: List[UnifiedGraftModel] = []
        for example in context.parsed.examples:
            description = (example.description or "").strip()
            snippet = (example.snippet or "").strip()
            if not description and not snippet:
                continue
            nodes.append(
                ugm_node(
                    UnifiedGraftModelType.COMMENT_EXAMPLE,
                    [description, COMMENT_LANGUAGE, snippet],
                )
            )
        if not nodes:
            return None
        return ugm_node(UnifiedGraftModelType.COMMENT_EXAMPLES_ARRAY, nodes)
