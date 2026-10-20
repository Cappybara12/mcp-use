"""Neutral in-band inline markup grammar for CommentDoc description fields.

Each technology embeds its own documentation language for type references
and inline code into description prose: Javadoc uses ``{@link Foo}`` and
``{@code expr}``; XMLDoc uses ``<see cref="Foo"/>`` and ``<c>expr</c>``;
JSDoc/PHPDoc use ``{@link Foo}`` and Markdown backticks; reST/Google
docstrings use Sphinx roles like ``:class:`Foo` `` and double-backtick
code; YARD uses ``{Foo}`` and Markdown backticks. Letting these tokens
flow verbatim through the Unified Graft Model means the Python code
generator would emit ``{@link Foo}`` inside a Python docstring (or
similar abominations cross-technology).

This module defines a *neutral* in-band grammar that survives the round
trip through UGM:

* ``{{ref:Target}}`` — type/symbol reference (replaces all source-specific
  link tags). ``Target`` is a single identifier or a dotted/hash chain
  (for instance ``Foo``, ``Foo.bar``, or ``Foo#bar``).
* ``{{code:expression}}`` — inline literal code (replaces all
  source-specific inline-code tags).
* ``\\n\\n`` — paragraph break (replaces ``<p>``/``<para>``).

Every analyzer calls ``encode_<source_style>`` before writing a
description string into the UGM payload; every generator calls
``decode_to_<target_style>`` before rendering the description back into
its target documentation language.

Constraints (documented, not enforced):

1. The neutral tokens never contain ``}}`` in the target/expression
   slot. A literal ``}}`` inside an inline code fragment would terminate
   the marker early. Real-world prose almost never produces this.
2. The encoders are *lossy with respect to display text*: Javadoc's
   ``{@link Foo display text}`` form keeps only ``Foo`` after the round
   trip. Linking metadata semantics survive; cosmetic display labels do
   not.
"""

from __future__ import annotations

import re
from typing import Pattern

REF_MARKER_OPEN = "{{ref:"
CODE_MARKER_OPEN = "{{code:"
MARKER_CLOSE = "}}"

_REF_PATTERN: Pattern[str] = re.compile(r"\{\{ref:([^}]+)\}\}")
_CODE_PATTERN: Pattern[str] = re.compile(r"\{\{code:([^}]+)\}\}")


def _ref(target: str) -> str:
    return f"{REF_MARKER_OPEN}{target.strip()}{MARKER_CLOSE}"


def _code(expr: str) -> str:
    return f"{CODE_MARKER_OPEN}{expr.strip()}{MARKER_CLOSE}"


# --------------------------------------------------------------------------- #
# Encoders: source-style → neutral
# --------------------------------------------------------------------------- #

_JAVADOC_LINK = re.compile(r"\{@link(?:plain)?\s+([^}\s]+)(?:\s+[^}]*)?\}")
_JAVADOC_CODE = re.compile(r"\{@code\s+([^}]+)\}")
_HTML_PARAGRAPH_OPEN = re.compile(r"<p\s*/?>", re.IGNORECASE)
_HTML_PARAGRAPH_CLOSE = re.compile(r"</p\s*>", re.IGNORECASE)
_HTML_CODE_INLINE = re.compile(r"<code>([^<]+)</code>", re.IGNORECASE)


def encode_javadoc(text: str) -> str:
    """Convert Javadoc inline tags into neutral markers."""
    if not text:
        return text
    out = _JAVADOC_LINK.sub(lambda m: _ref(m.group(1)), text)
    out = _JAVADOC_CODE.sub(lambda m: _code(m.group(1)), out)
    out = _HTML_CODE_INLINE.sub(lambda m: _code(m.group(1)), out)
    out = _HTML_PARAGRAPH_OPEN.sub("\n\n", out)
    out = _HTML_PARAGRAPH_CLOSE.sub("", out)
    return out


_XMLDOC_SEE = re.compile(r"<see(?:also)?\s+cref=\"([^\"]+)\"\s*/>", re.IGNORECASE)
_XMLDOC_PARAMREF = re.compile(r"<paramref\s+name=\"([^\"]+)\"\s*/>", re.IGNORECASE)
_XMLDOC_C = re.compile(r"<c>([^<]+)</c>", re.IGNORECASE)
_XMLDOC_PARA_OPEN = re.compile(r"<para\s*/?>", re.IGNORECASE)
_XMLDOC_PARA_CLOSE = re.compile(r"</para\s*>", re.IGNORECASE)
_XMLDOC_CREF_PREFIX = re.compile(r"^[TMFPE]:")


def _strip_cref(cref: str) -> str:
    """Drop the ``T:``/``M:``/``F:``/``P:``/``E:`` prefix and any namespace."""
    cref = _XMLDOC_CREF_PREFIX.sub("", cref)
    if "." in cref and "(" not in cref:
        return cref.rsplit(".", 1)[-1]
    return cref


def encode_xmldoc(text: str) -> str:
    """Convert XMLDoc inline tags into neutral markers."""
    if not text:
        return text
    out = _XMLDOC_SEE.sub(lambda m: _ref(_strip_cref(m.group(1))), text)
    out = _XMLDOC_PARAMREF.sub(lambda m: _code(m.group(1)), out)
    out = _XMLDOC_C.sub(lambda m: _code(m.group(1)), out)
    out = _XMLDOC_PARA_OPEN.sub("\n\n", out)
    out = _XMLDOC_PARA_CLOSE.sub("", out)
    return out


_JSDOC_LINK = re.compile(r"\{@link(?:code|plain)?\s+([^}\s|]+)(?:\s*\|[^}]*)?\}")
_JSDOC_BACKTICK = re.compile(r"`([^`\n]+)`")


def encode_jsdoc(text: str) -> str:
    """Convert JSDoc inline tags into neutral markers."""
    if not text:
        return text
    out = _JSDOC_LINK.sub(lambda m: _ref(m.group(1)), text)
    out = _JSDOC_BACKTICK.sub(lambda m: _code(m.group(1)), out)
    return out


_PHPDOC_LINK = re.compile(r"\{@(?:link|see)\s+([^}\s]+)(?:\s+[^}]*)?\}")
_PHPDOC_BACKTICK = _JSDOC_BACKTICK


def encode_phpdoc(text: str) -> str:
    """Convert PHPDoc inline tags into neutral markers."""
    if not text:
        return text
    out = _PHPDOC_LINK.sub(lambda m: _ref(m.group(1)), text)
    out = _PHPDOC_BACKTICK.sub(lambda m: _code(m.group(1)), out)
    return out


_RST_ROLE = re.compile(
    r":(?:py:)?(?:class|func|meth|attr|mod|obj|exc|data):`([^`]+)`"
)
_RST_DOUBLE_BACKTICK = re.compile(r"``([^`\n]+)``")


def encode_rst_google(text: str) -> str:
    """Convert reST/Google-docstring inline roles into neutral markers."""
    if not text:
        return text
    out = _RST_ROLE.sub(lambda m: _ref(m.group(1)), text)
    out = _RST_DOUBLE_BACKTICK.sub(lambda m: _code(m.group(1)), out)
    return out


_YARD_LINK = re.compile(r"\{([A-Z][A-Za-z0-9_]*(?:[#.][A-Za-z0-9_]+)?)(?:\s+[^}]+)?\}")
_YARD_BACKTICK = _JSDOC_BACKTICK


def encode_yard(text: str) -> str:
    """Convert YARD inline tags into neutral markers."""
    if not text:
        return text
    out = _YARD_LINK.sub(lambda m: _ref(m.group(1)), text)
    out = _YARD_BACKTICK.sub(lambda m: _code(m.group(1)), out)
    return out


# --------------------------------------------------------------------------- #
# Decoders: neutral → target-style
# --------------------------------------------------------------------------- #


def decode_to_javadoc(text: str) -> str:
    if not text:
        return text
    out = _REF_PATTERN.sub(lambda m: "{@link " + m.group(1).strip() + "}", text)
    out = _CODE_PATTERN.sub(lambda m: "{@code " + m.group(1).strip() + "}", out)
    return out


def decode_to_xmldoc(text: str) -> str:
    if not text:
        return text
    out = _REF_PATTERN.sub(
        lambda m: '<see cref="' + m.group(1).strip() + '"/>', text
    )
    out = _CODE_PATTERN.sub(lambda m: "<c>" + m.group(1).strip() + "</c>", out)
    return out


def decode_to_jsdoc(text: str) -> str:
    if not text:
        return text
    out = _REF_PATTERN.sub(lambda m: "{@link " + m.group(1).strip() + "}", text)
    out = _CODE_PATTERN.sub(lambda m: "`" + m.group(1).strip() + "`", out)
    return out


def decode_to_phpdoc(text: str) -> str:
    if not text:
        return text
    out = _REF_PATTERN.sub(lambda m: "{@link " + m.group(1).strip() + "}", text)
    out = _CODE_PATTERN.sub(lambda m: "`" + m.group(1).strip() + "`", out)
    return out


def _rst_role_for_target(target: str) -> str:
    """Choose a Sphinx role based on naming convention.

    Uppercase-first identifiers map to ``:class:``; identifiers containing
    ``#`` or ``.`` map to ``:meth:``; everything else maps to ``:func:``.
    """
    if "#" in target or ("." in target and target[:1].isupper()):
        return "meth"
    if target[:1].isupper():
        return "class"
    return "func"


def decode_to_rst_google(text: str) -> str:
    if not text:
        return text

    def _ref_repl(match: "re.Match[str]") -> str:
        target = match.group(1).strip().replace("#", ".")
        role = _rst_role_for_target(match.group(1).strip())
        return f":{role}:`{target}`"

    out = _REF_PATTERN.sub(_ref_repl, text)
    out = _CODE_PATTERN.sub(lambda m: "``" + m.group(1).strip() + "``", out)
    return out


def decode_to_yard(text: str) -> str:
    if not text:
        return text
    out = _REF_PATTERN.sub(lambda m: "{" + m.group(1).strip() + "}", text)
    out = _CODE_PATTERN.sub(lambda m: "`" + m.group(1).strip() + "`", out)
    return out


__all__ = [
    "encode_javadoc",
    "encode_xmldoc",
    "encode_jsdoc",
    "encode_phpdoc",
    "encode_rst_google",
    "encode_yard",
    "decode_to_javadoc",
    "decode_to_xmldoc",
    "decode_to_jsdoc",
    "decode_to_phpdoc",
    "decode_to_rst_google",
    "decode_to_yard",
]
