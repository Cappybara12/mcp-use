"""Runtime configuration for the Module Analyzer (Python).

Exposes booleans the analyzer reads when building UGM payloads. Today the
only flag is ``should_emit_code_examples``, which gates ``COMMENT_EXAMPLES_ARRAY``
and the ``raw`` field of ``COMMENT_SOURCE`` (Policy B — no source fragments
by default).

The flag is read from the environment on every call (not cached) so tests
can flip ``GRAFTCODE_GMA_EMIT_CODE_EXAMPLES`` without import-order issues.
"""

from __future__ import annotations

import os

ENV_EMIT_CODE_EXAMPLES = "GRAFTCODE_GMA_EMIT_CODE_EXAMPLES"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def should_emit_code_examples() -> bool:
    """Return True when the analyzer may embed source code in UGM."""
    raw = os.environ.get(ENV_EMIT_CODE_EXAMPLES, "")
    return raw.strip().lower() in _TRUTHY
