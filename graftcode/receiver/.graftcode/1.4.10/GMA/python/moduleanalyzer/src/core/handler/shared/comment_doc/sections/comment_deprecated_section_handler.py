from __future__ import annotations

from typing import Optional

from graftcode_protocol.commentdoc.inline_markup import encode_rst_google
from graftcode_protocol.commentdoc.version_utils import looks_like_version
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentDeprecatedSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        deprecation = context.parsed.deprecation
        if deprecation is None:
            return None

        version = (deprecation.version or "").strip()
        description = encode_rst_google((deprecation.description or "").strip())

        message_parts: list[str] = []
        if version:
            message_parts.append(f"Since {version}.")
        if description:
            message_parts.append(description)

        message = " ".join(message_parts).strip()
        replacement = ""
        if version and not looks_like_version(version):
            replacement = version
            message = description

        if not message and not replacement:
            return None

        return ugm_node(
            UnifiedGraftModelType.COMMENT_DEPRECATED,
            [True, message, replacement],
        )
