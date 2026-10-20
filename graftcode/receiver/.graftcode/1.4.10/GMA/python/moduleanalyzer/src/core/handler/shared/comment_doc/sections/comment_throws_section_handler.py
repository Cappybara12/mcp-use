from __future__ import annotations

from typing import List, Optional

from graftcode_protocol.commentdoc import exception_mapping as em
from graftcode_protocol.commentdoc.inline_markup import encode_rst_google
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentThrowsSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        nodes: List[UnifiedGraftModel] = []
        for entry in context.parsed.raises:
            raw_type = (entry.type_name or "").strip()
            description = encode_rst_google((entry.description or "").strip())
            if not raw_type and not description:
                continue
            nodes.append(
                ugm_node(
                    UnifiedGraftModelType.COMMENT_THROW,
                    [raw_type, em.raw_to_category(raw_type), description],
                )
            )
        if not nodes:
            return None
        return ugm_node(UnifiedGraftModelType.COMMENT_THROWS_ARRAY, nodes)
