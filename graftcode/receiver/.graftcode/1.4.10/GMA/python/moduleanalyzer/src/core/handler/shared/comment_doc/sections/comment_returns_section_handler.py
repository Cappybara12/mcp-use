from __future__ import annotations

from typing import Optional

from graftcode_protocol.commentdoc.inline_markup import encode_rst_google
from graftcode_protocol.commentdoc.type_mapping import python_raw_to_normalized
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentReturnsSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        returns = context.parsed.returns
        if returns is None:
            return None
        raw_type = (returns.type_name or "").strip()
        description = encode_rst_google((returns.description or "").strip())
        if not raw_type and not description:
            return None
        return ugm_node(
            UnifiedGraftModelType.COMMENT_RETURNS,
            [
                raw_type,
                python_raw_to_normalized(raw_type),
                description,
                "null" in raw_type.lower() or "none" in raw_type.lower(),
            ],
        )
