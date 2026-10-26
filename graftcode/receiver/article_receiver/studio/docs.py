"""Turn an HTML page or a markdown document into a small structured summary (a "Doc")."""
from __future__ import annotations

import html
import json
import re
import urllib.parse
from html.parser import HTMLParser

_SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "template"}
_FAQ_HEADING = re.compile(r"^(faq|frequently asked questions|common questions|questions)\b", re.I)


def words_in(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text))


class _HTMLDoc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.headings: list[tuple[int, str]] = []
        self.paragraphs: list[str] = []
        self.seq: list[tuple[str, str]] = []   # headings and paragraphs in page order
        self.links: list[tuple[str, str]] = []
        self.jsonld: list[str] = []
        self.bold = 0
        self.lists = 0
        self.images = 0
        self.tables = 0
        self._skip = 0
        self._tag = ""
        self._buf: list[str] = []
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_buf: list[str] = []
        self._href = ""
        self._link_buf: list[str] = []
        self._in_article = 0
        self._article_seen = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and (a.get("name") or "").lower() == "description":
            self.description = (a.get("content") or "").strip()
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href") or ""
        elif tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = []
        elif tag in ("article", "main"):
            self._in_article += 1
            self._article_seen = True
        if tag in _SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "p", "li", "summary"):
            self._tag, self._buf = tag, []
        elif tag in ("strong", "b"):
            self.bold += 1
        elif tag in ("ul", "ol"):
            self.lists += 1
        elif tag == "img":
            self.images += 1
        elif tag == "table":
            self.tables += 1
        elif tag == "a" and a.get("href"):
            self._href, self._link_buf = a["href"], []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld.append("".join(self._jsonld_buf))
        elif tag in ("article", "main"):
            self._in_article = max(0, self._in_article - 1)
        if tag in _SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == self._tag:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                if tag in ("h1", "h2", "h3", "h4"):
                    self.headings.append((int(tag[1]), text))
                    self.seq.append((tag, text))
                elif tag in ("p", "summary") or (tag == "li" and words_in(text) > 12):
                    self.paragraphs.append(text)
                    self.seq.append(("p", text))
            self._tag, self._buf = "", []
        elif tag == "a" and self._href:
            self.links.append((re.sub(r"\s+", " ", "".join(self._link_buf)).strip(), self._href))
            self._href = ""

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_jsonld:
            self._jsonld_buf.append(data)
        if self._skip:
            return
        if self._tag:
            self._buf.append(data)
        if self._href:
            self._link_buf.append(data)


def _jsonld_types(blocks: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    types, pairs = [], []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            t = node.get("@type")
            for name in (t if isinstance(t, list) else [t]):
                if isinstance(name, str):
                    types.append(name)
            if node.get("@type") == "Question":
                answer = node.get("acceptedAnswer") or {}
                pairs.append((str(node.get("name", "")), re.sub(r"<[^>]+>", "", str(answer.get("text", "")))))
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)

    for block in blocks:
        try:
            walk(json.loads(block))
        except (json.JSONDecodeError, ValueError):
            continue
    return types, pairs


def _faq_pairs(headings_and_text: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Pairs a question heading ('...?') with the text that follows, inside an FAQ section."""
    pairs, in_faq, question = [], False, None
    for kind, text in headings_and_text:
        if kind in ("h1", "h2"):
            in_faq = bool(_FAQ_HEADING.match(text.strip()))
            question = None
        elif kind in ("h3", "h4") and (in_faq or text.strip().endswith("?")) and text.strip().endswith("?"):
            if in_faq:
                question = text.strip()
        elif kind == "p" and question:
            pairs.append((question, text.strip()))
            question = None
    return pairs


def parse_html(source: str, page_url: str = "") -> dict:
    parser = _HTMLDoc()
    parser.feed(source)
    host = urllib.parse.urlparse(page_url).netloc.lower().removeprefix("www.")
    internal = external = 0
    for _text, href in parser.links:
        parsed = urllib.parse.urlparse(urllib.parse.urljoin(page_url, href))
        if parsed.scheme not in ("http", "https"):
            continue
        if host and parsed.netloc.lower().removeprefix("www.") == host:
            internal += 1
        else:
            external += 1
    types, schema_pairs = _jsonld_types(parser.jsonld)
    h1 = next((t for lvl, t in parser.headings if lvl == 1), "")
    title = h1 or html.unescape(re.sub(r"\s+", " ", parser.title)).strip()
    text = "\n\n".join(parser.paragraphs)
    faq_pairs = schema_pairs or _faq_pairs(parser.seq)
    return {
        "title": title, "description": parser.description, "canonical": parser.canonical,
        "headings": parser.headings, "paragraphs": parser.paragraphs, "text": text, "words": words_in(text),
        "internal_links": internal, "external_links": external,
        "bold": parser.bold, "lists": parser.lists, "images": parser.images, "tables": parser.tables,
        "jsonld_types": sorted(set(types)), "has_faq_schema": "FAQPage" in types,
        "faq_pairs": faq_pairs,
        "has_faq_heading": any(_FAQ_HEADING.match(t) for lvl, t in parser.headings if lvl <= 2),
    }


_MD_HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
_MD_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)[^)]*\)")


def parse_markdown(source: str, page_url: str = "") -> dict:
    body = source
    meta_title = ""
    front = re.match(r"^---\n(.*?)\n---\n", source, re.S)
    if front:
        body = source[front.end():]
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", front.group(1), re.M)
        meta_title = m.group(1) if m else ""
    headings: list[tuple[int, str]] = []
    paragraphs: list[str] = []
    seq: list[tuple[str, str]] = []
    para: list[str] = []
    bold = lists = images = 0
    in_code = False

    def flush():
        if para:
            text = " ".join(para).strip()
            if text:
                paragraphs.append(text)
                seq.append(("p", text))
            para.clear()

    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            flush()
            continue
        if in_code:
            continue
        m = _MD_HEADING.match(line)
        if m:
            flush()
            level, text = len(m.group(1)), m.group(2).strip()
            headings.append((level, text))
            seq.append((f"h{level}", text))
        elif not line.strip():
            flush()
        elif re.match(r"^\s*([-*+]|\d+\.)\s+", line):
            flush()
            lists += 1 if not (seq and seq[-1][0] == "li") else 0
            seq.append(("li", line.strip()))
            if words_in(line) > 12:
                paragraphs.append(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", line).strip())
        elif line.strip().startswith(">"):
            continue
        else:
            para.append(line.strip())
    flush()
    tables = 0
    prose = re.sub(r"```.*?```", "", body, flags=re.S)           # a table inside a code block is not a table
    rows = prose.splitlines()
    for i in range(len(rows) - 1):
        if "|" in rows[i] and re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", rows[i + 1]):
            tables += 1
    bold = len(re.findall(r"\*\*[^*\n]+\*\*", body))
    images = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", body))
    host = urllib.parse.urlparse(page_url).netloc.lower().removeprefix("www.")
    internal = external = 0
    for _t, href in _MD_LINK.findall(body):
        parsed = urllib.parse.urlparse(urllib.parse.urljoin(page_url, href))
        if parsed.scheme in ("http", "https"):
            if host and parsed.netloc.lower().removeprefix("www.") == host:
                internal += 1
            else:
                external += 1
        elif not parsed.scheme:
            internal += 1
    for bare in re.findall(r"(?<![\(\[])https?://[^\s)>\]]+", body):   # plain URLs not inside [text](url)
        if host and urllib.parse.urlparse(bare).netloc.lower().removeprefix("www.") == host:
            internal += 1
        else:
            external += 1
    h1 = next((t for lvl, t in headings if lvl == 1), "") or meta_title
    text = "\n\n".join(paragraphs)
    pairs = _faq_pairs(seq)
    return {
        "title": h1, "description": "", "canonical": "", "headings": headings, "paragraphs": paragraphs,
        "text": text, "words": words_in(text), "internal_links": internal, "external_links": external,
        "bold": bold, "lists": lists, "images": images, "tables": tables, "jsonld_types": [], "has_faq_schema": False,
        "faq_pairs": pairs, "has_faq_heading": any(_FAQ_HEADING.match(t) for lvl, t in headings if lvl <= 2),
    }


def parse_document(source: str, kind: str, page_url: str = "") -> dict:
    return parse_html(source, page_url) if kind == "html" else parse_markdown(source, page_url)
