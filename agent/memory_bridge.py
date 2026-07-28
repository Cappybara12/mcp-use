"""
Bridge into the 24-7-chronically-online project's ChromaDB memory store.

Used to answer one question reliably: "has Wayzyy already covered this topic?" —
checked against both the live published blog AND locally-written drafts (embedded
here the moment they're saved, so we don't re-suggest something written an hour
ago but not yet published).
"""

import os
import sys
from pathlib import Path

CHRONICALLY_ONLINE_DIR = (Path(__file__).parent / ".." / ".." / "24-7-chronically-online").resolve()

_store = None  # lazy singleton — avoids reloading the embedding model on every call


def get_memory_store():
    global _store
    if _store is not None:
        return _store

    if str(CHRONICALLY_ONLINE_DIR) not in sys.path:
        sys.path.insert(0, str(CHRONICALLY_ONLINE_DIR))

    from memory.store import MemoryStore  # noqa: E402

    # MemoryStore.load_config() reads "config.yaml" relative to cwd, so we
    # need cwd pointed at the chronically-online project for just this call.
    old_cwd = os.getcwd()
    os.chdir(CHRONICALLY_ONLINE_DIR)
    try:
        _store = MemoryStore()
    finally:
        os.chdir(old_cwd)

    return _store


def is_topic_covered(topic: str, threshold: float = 0.7) -> tuple[bool, list[dict]]:
    """
    True if a similar article already exists (published or drafted locally).
    Uses title-level matching, not body chunks — titles are short and concise,
    so they discriminate between topics far better than diluted 500-word chunks
    (verified: chunk search buried an exact-title match at rank 7; title search
    puts it at rank 1). Returns (covered, related_articles) for callers to show.
    """
    store = get_memory_store()
    hits = store.search_titles(topic, top_k=3)
    if not hits:
        return False, []
    covered = hits[0]["score"] >= threshold
    return covered, hits


def embed_draft(topic: str, title: str, article_text: str, filepath: str):
    """Embed a freshly-written local draft into the same corpus used for
    dedup, so it counts as 'covered' immediately — before it's ever published."""
    store = get_memory_store()  # must run first — this is what puts corpus/ on sys.path
    from corpus.scraper import chunk_article
    chunks = chunk_article({
        "url": f"local-draft://{filepath}",
        "title": title or topic,
        "content": article_text,
    })
    store.add_articles(chunks)
