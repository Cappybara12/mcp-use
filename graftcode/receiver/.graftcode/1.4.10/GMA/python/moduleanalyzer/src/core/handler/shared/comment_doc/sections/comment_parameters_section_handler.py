from __future__ import annotations

from typing import List, Optional

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


class CommentParametersSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        nodes: List[UnifiedGraftModel] = []
        for param in context.parsed.params:
            name = (param.arg_name or "").strip()
            raw_type = (param.type_name or "").strip()
            description = encode_rst_google((param.description or "").strip())
            is_required = not bool(param.is_optional)
            is_nullable = "null" in raw_type.lower() or "none" in raw_type.lower()
            default_value = "" if param.default is None else str(param.default)
            if not name and not raw_type and not description:
                continue
            nodes.append(
                ugm_node(
                    UnifiedGraftModelType.COMMENT_PARAMETER,
                    [
                        name,
                        raw_type,
                        python_raw_to_normalized(raw_type),
                        description,
                        is_required,
                        is_nullable,
                        default_value,
                    ],
                )
            )
        if not nodes:
            return None
        return ugm_node(UnifiedGraftModelType.COMMENT_PARAMETERS_ARRAY, nodes)
