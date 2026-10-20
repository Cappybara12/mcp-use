"""Factory helpers for CommentDoc UGM nodes."""

from __future__ import annotations

from typing import Any, List, Optional

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

COMMENT_LANGUAGE = "python"
COMMENT_STYLE_GOOGLE = "google"
COMMENT_STYLE_NUMPY = "numpy"
COMMENT_STYLE_REST = "rest"


def normalize_source_file_name(path: str) -> str:
    if not path:
        return ""

    if path.startswith("classpath:"):
        path = path[len("classpath:") :]

    normalized = path.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]

    return basename if basename else path


def ugm_node(
    graft_type: UnifiedGraftModelType,
    payload: Optional[List[Any]] = None,
) -> UnifiedGraftModel:
    return UnifiedGraftModel(RuntimeName.Python, graft_type, payload or [])
