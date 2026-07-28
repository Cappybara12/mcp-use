"""
Research — deterministic Firecrawl search + scrape for a chosen topic,
then one LLM call to synthesize a research brief. No autonomous agent loop:
we decide exactly what gets searched, in code, so this is cheap and reliable
instead of letting a reasoning model burn tokens deciding what to search next.
"""

import sys
import os
from firecrawl import FirecrawlApp
from openai import OpenAI
from agent.utils import with_retry

MAX_SOURCES = 4
MAX_CHARS_PER_SOURCE = 4000


SYNTHESIS_PROMPT = """
You are a research assistant for a Goa travel blog called Wayzyy.

TOPIC: {topic}

Below is raw scraped content from competitor articles and Reddit threads about this topic.
Read all of it, then produce a structured research brief.

--- RAW SOURCES ---
{raw_sources}
--- END RAW SOURCES ---

Return your answer in exactly this format:

COMPETITOR ANALYSIS:
- What H2 headings do most articles use?
- What do they all cover? (the basics)
- What do NONE of them cover? (the gaps — this is most important)
- What practical info is missing? (costs, ATMs, parking, network, timings)

REAL QUESTIONS PEOPLE ASK:
- List every real question found in the sources above (verbatim where possible)

KEY FACTS TO INCLUDE:
- Any concrete facts found: costs (₹), distances, timings, recent changes

LOCAL/INSIDER INFO:
- Any tips, complaints, or things locals/visitors mentioned that guides usually skip

CONTENT GAPS (most important):
- What's missing from all these sources that a traveler actually needs?
- What would make Wayzyy's article 10x more useful than what's ranking?

---INCIDENTAL TOPICS---
List any OTHER distinct Goa travel topics mentioned in the sources above that are
NOT about "{topic}" itself — e.g. a different beach, a new law, a seasonal event,
a different accommodation trend. One per line, just the short topic phrase, no
explanation. If nothing else was mentioned, write "None".
"""


# Firecrawl can't scrape these — don't waste scrape attempts on them, and
# don't let them crowd out scrapable sources when collecting candidates
# (confirmed failure mode: a topic whose top web results were all Instagram
# posts returned zero usable sources even though the search itself matched
# correctly).
UNSCRAPABLE_DOMAINS = ["instagram.com", "facebook.com", "tiktok.com", "x.com", "twitter.com"]


def _search_and_scrape(app: FirecrawlApp, topic: str) -> list[dict]:
    """Run a small, fixed set of specific searches for this exact topic and
    scrape the top results. No LLM involved in deciding what to search."""
    candidates = []

    queries = [
        (f'"{topic}" Goa guide 2026', {}),
        (f'"{topic}"', {"include_domains": ["reddit.com"]}),
    ]

    urls_seen = set()
    for query, extra_kwargs in queries:
        try:
            result = app.search(query, limit=6, **extra_kwargs)
            hits = getattr(result, "web", None) or getattr(result, "data", None) or []
        except Exception as e:
            print(f"[researcher] Search failed for '{query}': {e}", file=sys.stderr)
            continue

        for hit in hits:
            url = getattr(hit, "url", None) or (hit.get("url") if isinstance(hit, dict) else None)
            title = getattr(hit, "title", None) or (hit.get("title") if isinstance(hit, dict) else "") or url
            if not url or url in urls_seen:
                continue
            if any(d in url for d in UNSCRAPABLE_DOMAINS):
                continue
            urls_seen.add(url)
            candidates.append({"url": url, "title": title})

    # Scrape candidates in order, keep going past failures until we hit
    # MAX_SOURCES successes or run out — a few unscrapable/broken pages
    # shouldn't mean the whole research step comes back empty.
    scraped = []
    for s in candidates:
        if len(scraped) >= MAX_SOURCES:
            break
        try:
            doc = app.scrape(s["url"], formats=["markdown"], only_main_content=True, timeout=15000)
            content = getattr(doc, "markdown", None) or ""
            if content:
                scraped.append({"url": s["url"], "title": s["title"], "content": content[:MAX_CHARS_PER_SOURCE]})
        except Exception as e:
            print(f"[researcher] Scrape failed for {s['url']}: {e}", file=sys.stderr)
            continue

    return scraped


def _get_llm_client() -> OpenAI:
    return OpenAI(api_key=os.environ["KIMI_API_KEY"], base_url="https://api.moonshot.ai/v1")


def run_research(topic: str, known_sources: list[dict] = None) -> dict:
    """
    Deterministic research: fixed Firecrawl searches + scrapes for this exact
    topic, then one LLM call to synthesize a brief. Also returns any
    incidental other-topic mentions found along the way.

    known_sources: real headlines/URLs already found for this topic during
    discovery (from the review queue file), used as a fallback when live
    scraping finds nothing. Confirmed failure mode: a very fresh news story
    (e.g. a same-week government announcement) can exist only on Instagram,
    which Firecrawl can't scrape — without this fallback, research returns
    completely empty and the writer falls back to pure generic knowledge,
    producing an article that never mentions the actual news hook.
    """
    print(f"\n[researcher] Starting research for: {topic}", file=sys.stderr)

    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
    scraped = _search_and_scrape(app, topic)

    if not scraped and known_sources:
        print(f"[researcher] Live scrape found nothing — falling back to {len(known_sources)} known headline(s) from discovery.", file=sys.stderr)
        scraped = [
            {"url": s.get("url", ""), "title": s["title"], "content": f"(Headline only, from {s.get('platform', 'a news source')} — full article wasn't scrapable)"}
            for s in known_sources if s.get("title")
        ]

    if not scraped:
        print("[researcher] No sources found — proceeding with limited context.", file=sys.stderr)
        return {
            "topic": topic,
            "brief": f"No research sources found for '{topic}'. Write from general Goa travel knowledge.",
            "incidental_topics": [],
            "status": "failed",
        }

    raw_sources = "\n\n".join(
        f"[{s['title']}]({s['url']})\n{s['content']}" for s in scraped
    )

    prompt = SYNTHESIS_PROMPT.format(topic=topic, raw_sources=raw_sources[:16000])

    client = _get_llm_client()
    try:
        from agent.utils import call_with_fallback
        response = call_with_fallback(
            lambda: client.chat.completions.create(
                model="kimi-k2.7-code-highspeed",
                messages=[{"role": "user", "content": prompt}],
                temperature=1, max_tokens=3000,
            ),
            lambda: OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1").chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=1500,
            ),
        )
        full_text = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[researcher] Synthesis failed: {e}", file=sys.stderr)
        return {
            "topic": topic,
            "brief": f"Research synthesis failed: {e}. Proceeding with limited context.",
            "incidental_topics": [],
            "status": "failed",
        }

    # Split off the incidental-topics section
    brief = full_text
    incidental_topics = []
    marker = "---INCIDENTAL TOPICS---"
    if marker in full_text:
        brief, incidental_raw = full_text.split(marker, 1)
        for line in incidental_raw.strip().split("\n"):
            line = line.strip("-• \t")
            if line and line.lower() != "none":
                incidental_topics.append(line)

    print(f"[researcher] Research complete. {len(scraped)} sources, {len(incidental_topics)} incidental topics found.", file=sys.stderr)

    return {
        "topic": topic,
        "brief": brief.strip(),
        "incidental_topics": incidental_topics,
        "status": "success",
    }


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Tambdi Surla Temple Goa"
    result = run_research(topic)
    print("\n" + "=" * 60, file=sys.stderr)
    print(result["brief"], file=sys.stderr)
    print("\nIncidental topics:", result["incidental_topics"], file=sys.stderr)
