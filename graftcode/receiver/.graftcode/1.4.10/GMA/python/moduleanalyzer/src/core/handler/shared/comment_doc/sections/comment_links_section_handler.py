from __future__ import annotations

from typing import List, Optional

from graftcode_protocol.commentdoc.docstring_sections import extract_see_also_links
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentLinksSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        nodes: List[UnifiedGraftModel] = []
        for item in context.parsed.meta:
            if item.args and item.args[0].lower() in {"see", "link", "seealso"}:
                target = " ".join(item.args[1:]).strip() if len(item.args) > 1 else ""
                if not target:
                    target = (item.description or "").strip()
                if target:
                    kind = item.args[0].lower()
                    nodes.append(
                        ugm_node(
                            UnifiedGraftModelType.COMMENT_LINK,
                            [target, "", kind],
                        )
                    )
        for target, label, kind in extract_see_also_links(context.raw_doc):
            nodes.append(
                ugm_node(
                    UnifiedGraftModelType.COMMENT_LINK,
                    [target, label, kind],
                )
            )
        if not nodes:
            return None
        return ugm_node(UnifiedGraftModelType.COMMENT_LINKS_ARRAY, nodes)
