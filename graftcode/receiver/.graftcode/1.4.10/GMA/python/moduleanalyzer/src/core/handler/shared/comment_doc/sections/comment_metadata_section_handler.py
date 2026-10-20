from __future__ import annotations

from typing import Optional

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    ugm_node,
)


class CommentMetadataSectionHandler:
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]:
        buckets = {
            "author": [],
            "since": [],
            "version": [],
            "license": [],
            "tags": [],
        }
        for item in context.parsed.meta:
            key = (item.args[0] if item.args else "").lower()
            value = (item.description or " ".join(item.args[1:])).strip()
            if key in buckets and value:
                buckets[key].append(value)

        author = "; ".join(buckets["author"])
        since = "; ".join(buckets["since"])
        version = "; ".join(buckets["version"])
        license_ = "; ".join(buckets["license"])
        tags = "; ".join(buckets["tags"])
        if not any((author, since, version, license_, tags)):
            return None
        return ugm_node(
            UnifiedGraftModelType.COMMENT_METADATA,
            [author, since, version, license_, tags],
        )
