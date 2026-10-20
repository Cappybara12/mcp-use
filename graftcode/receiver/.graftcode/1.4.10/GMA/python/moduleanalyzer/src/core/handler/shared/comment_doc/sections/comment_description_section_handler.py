from __future__ import annotations

from typing import Optional

from graftcode_protocol.commentdoc.docstring_sections import (
    strip_see_also_from_description,
)
from graftcode_protocol.commentdoc.inline_markup import encode_rst_google
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentDescriptionSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        description = (context.parsed.long_description or "").strip()
        description = strip_see_also_from_description(description)
        if not description:
            return None
        return ugm_node(
            UnifiedGraftModelType.COMMENT_DESCRIPTION,
            [encode_rst_google(description)],
        )
