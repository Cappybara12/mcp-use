"""Reading feeds and blogs: RSS/Atom parsing, post discovery from a site URL, bundled samples."""
from __future__ import annotations

import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from . import docs, providers
from .net import NetError, fetch_public
from .store import StudioError

MAX_FEED_BYTES = 2_000_000
_COMMON_FEEDS = ("/feed", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml", "/blog/rss.xml", "/blog/feed")


def sample_dir() -> Path:
    # The studio package is imported from the real receiver folder, so __file__ is reliable here.
    return Path(os.environ.get("STUDIO_SAMPLE_DIR") or Path(__file__).resolve().parents[2] / "sample_data" / "studio")


def read_sample(url: str) -> tuple[str, str]:
    """'sample:feed/<name>' or 'sample:post/<name>' -> (text, kind)."""
    kind, _, name = url[len("sample:"):].partition("/")
    if kind not in ("feed", "post") or not re.fullmatch(r"[a-z0-9_-]{1,40}", name):
        raise StudioError("Unknown sample. Use sample:feed/<name> or sample:post/<name>.")
    folder = "feeds" if kind == "feed" else "blog"
    path = sample_dir() / folder / (f"{name}.xml" if kind == "feed" else f"{name}.html")
    if not path.is_file():
        raise StudioError(f"No such sample: {url}")
    return path.read_text(encoding="utf-8"), ("xml" if kind == "feed" else "html")


def list_sample_posts() -> list[str]:
    folder = sample_dir() / "blog"
    return [f"sample:post/{p.stem}" for p in sorted(folder.glob("*.html"))] if folder.is_dir() else []


# ── RSS / Atom ────────────────────────────────────────────────────────────────

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node, *names) -> str:
    for child in node:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def parse_feed(xml_bytes: bytes) -> list[dict]:
    head = xml_bytes[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in xml_bytes[:20000].lower():
        raise StudioError("This feed uses XML entity declarations, which are not allowed.")
    if len(xml_bytes) > MAX_FEED_BYTES:
        raise StudioError("The feed is too large.")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise StudioError(f"The feed is not valid XML: {exc}") from exc
    items = []
    for node in root.iter():
        name = _local(node.tag)
        if name not in ("item", "entry"):
            continue
        link = _text(node, "link")
        if not link:
            for child in node:
                if _local(child.tag) == "link" and child.get("href"):
                    link = child.get("href")
                    break
        summary = re.sub(r"<[^>]+>", " ", _text(node, "description", "summary", "content"))
        items.append({
            "title": re.sub(r"\s+", " ", _text(node, "title")), "link": link,
            "summary": re.sub(r"\s+", " ", summary).strip()[:400],
            "published": _text(node, "pubDate", "published", "updated", "date"),
        })
    return [i for i in items if i["title"]]


def read_feed(url: str) -> list[dict]:
    if url.startswith("sample:"):
        text, _ = read_sample(url)
        return parse_feed(text.encode("utf-8"))
    resp = fetch_public(url, max_bytes=MAX_FEED_BYTES)
    if resp.status != 200:
        raise NetError(f"The feed returned HTTP {resp.status}.")
    return parse_feed(resp.body)


# ── finding a blog's posts from a site URL ────────────────────────────────────

def discover_posts(site_url: str, limit: int) -> list[str]:
    """Find post URLs: the page's advertised feed, common feed paths, then the sitemap."""
    if site_url.startswith("sample:"):
        return list_sample_posts()[:limit]
    base = site_url.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []
    try:
        page = fetch_public(site_url)
        if page.status == 200:
            for m in re.finditer(r"<link[^>]+type=[\"']application/(?:rss|atom)\+xml[\"'][^>]*>", page.text(), re.I):
                href = re.search(r"href=[\"']([^\"']+)", m.group(0))
                if href:
                    candidates.append(urllib.parse.urljoin(site_url, href.group(1)))
    except NetError:
        pass
    candidates += [root + path for path in _COMMON_FEEDS]
    for feed_url in dict.fromkeys(candidates):
        try:
            links = [i["link"] for i in read_feed(feed_url) if i["link"]]
        except (NetError, StudioError):
            continue
        if links:
            return links[:limit]
    try:
        sm = fetch_public(root + "/sitemap.xml", max_bytes=MAX_FEED_BYTES)
        if sm.status == 200:
            urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm.text())
            posts = [u for u in urls if re.search(r"/(blog|posts?|articles?|guides?|news)/[^/]+/?$", u)]
            same_host = [u for u in posts if urllib.parse.urlparse(u).netloc == parsed.netloc]
            if same_host:
                return same_host[:limit]
    except NetError:
        pass
    raise StudioError("Could not find any posts. Paste a few post URLs in the node instead.")


# ── fetching pages as analysable documents ────────────────────────────────────

def fetch_document(url: str, provider: str, key: str = "") -> dict:
    """Return {'url','kind','source'} where kind is 'html' or 'markdown'."""
    if url.startswith("sample:"):
        text, kind = read_sample(url)
        return {"url": url, "kind": kind, "source": text}
    if provider == "tinyfish":
        results, errors = providers.tinyfish_fetch(key, [url], "markdown")
        if results and results[0].get("text"):
            return {"url": url, "kind": "markdown", "source": str(results[0]["text"]), "title": results[0].get("title") or ""}
        reason = errors[0].get("error") if errors else "empty_content"
        raise NetError(f"TinyFish could not read {url} ({reason}).")
    resp = fetch_public(url)
    if resp.status != 200:
        raise NetError(f"{url} returned HTTP {resp.status}.")
    if "html" not in resp.headers.get("content-type", "html"):
        raise NetError(f"{url} is not an HTML page.")
    return {"url": url, "kind": "html", "source": resp.text()}


def to_analysed(doc_info: dict) -> dict:
    return docs.parse_document(doc_info["source"], doc_info["kind"], doc_info["url"])
