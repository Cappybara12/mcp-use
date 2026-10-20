"""Protocol for CommentDoc section handlers."""

from __future__ import annotations

from typing import Optional, Protocol

from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_build_context import (
    CommentDocBuildContext,
)


class CommentDocSectionHandler(Protocol):
    def build_section(
        self, context: CommentDocBuildContext
    ) -> Optional[UnifiedGraftModel]: ...
