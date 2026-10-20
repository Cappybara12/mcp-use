"""Shared helpers for identifying Python stdlib/framework modules."""

from __future__ import annotations

_FRAMEWORK_MODULES = frozenset(
    {
        "builtins",
        "typing",
        "typing_extensions",
        "collections.abc",
        "abc",
    }
)

_FRAMEWORK_MODULE_ROOTS = frozenset(
    {
        "builtins",
        "datetime",
        "pathlib",
        "collections",
        "typing",
        "typing_extensions",
        "abc",
    }
)


def is_framework_module(module_name: str) -> bool:
    """Returns True for stdlib/builtin modules (abc, typing, etc.)."""
    if not module_name:
        return False
    if module_name in _FRAMEWORK_MODULES:
        return True
    return module_name.split(".")[0] in _FRAMEWORK_MODULE_ROOTS
