"""Map docstring_parser styles to CommentDoc source style labels."""

from __future__ import annotations

from typing import Optional

from docstring_parser import DocstringStyle

from moduleanalyzer.src.core.handler.shared.comment_doc.comment_doc_ugm_factory import (
    COMMENT_STYLE_GOOGLE,
    COMMENT_STYLE_NUMPY,
    COMMENT_STYLE_REST,
)

_STYLE_TO_COMMENT_STYLE = {
    DocstringStyle.GOOGLE: COMMENT_STYLE_GOOGLE,
    DocstringStyle.NUMPYDOC: COMMENT_STYLE_NUMPY,
    DocstringStyle.REST: COMMENT_STYLE_REST,
    DocstringStyle.EPYDOC: COMMENT_STYLE_REST,
}


def comment_style(detected: Optional[DocstringStyle]) -> str:
    if detected is not None:
        mapped = _STYLE_TO_COMMENT_STYLE.get(detected)
        if mapped:
            return mapped
    return COMMENT_STYLE_GOOGLE
