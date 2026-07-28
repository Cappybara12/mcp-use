#!/usr/bin/env python3
"""
Wayzyy Article Writer — MCP Server

Exposes the full article pipeline as MCP tools so you can trigger it
directly from Claude chat.

Tools:
  - list_pending_topics()     → show what's in the review queue
  - write_article(topic)      → run full pipeline, return draft
  - get_draft(slug)           → read a saved draft
  - list_drafts()             → show all saved drafts
  - run_style_check(slug)     → run style check on an existing draft
"""

import os
import sys
import re
import asyncio
from pathlib import Path
from datetime import datetime

from fastmcp import FastMCP
from dotenv import load_dotenv

# Load env from the article-writer directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

sys.path.insert(0, str(Path(__file__).parent))

mcp = FastMCP("wayzyy-article-writer")

DRAFTS_DIR = Path(__file__).parent / "drafts"
REVIEW_DIR = Path(__file__).parent / ".." / "24-7-chronically-online" / "review"


def _get_known_sources_for_topic(topic: str) -> list[dict]:
    """Look up the review queue file for this exact topic and return its
    already-known sources — real headlines/URLs collected during discovery,
    used as a research fallback when live scraping finds nothing (confirmed
    failure mode for very fresh news stories that only exist on Instagram)."""
    if not REVIEW_DIR.exists():
        return []
    for fname in REVIEW_DIR.iterdir():
        if fname.suffix != ".md":
            continue
        content = fname.read_text()
        if topic not in content:
            continue
        sources = []
        for m in re.finditer(r"^- \[(\w+)\] \[([^\]]+)\]\(([^)]+)\)", content, re.MULTILINE):
            platform, title, url = m.groups()
            sources.append({"platform": platform, "title": title, "url": url})
        if sources:
            return sources
    return []


def _save_incidental_topic(topic: str, origin_topic: str) -> None:
    """Save a topic idea surfaced incidentally while researching another
    article. Reuses the scanner's own save_topic() format so it shows up in
    the same review queue, already confirmed not-yet-covered by the caller."""
    chronically_online_dir = (Path(__file__).parent / ".." / "24-7-chronically-online").resolve()
    if str(chronically_online_dir) not in sys.path:
        sys.path.insert(0, str(chronically_online_dir))
    from review.queue import save_topic

    rag_result = {
        "group": {
            "keyword": topic,
            "sources": [{
                "platform": "research",
                "title": f"Mentioned while researching '{origin_topic}'",
                "url": "",
                "description": "",
            }],
        },
        "classification": "new_pillar",
        "related_articles": [],
        "top_similarity": 0.0,
    }
    save_topic(rag_result)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


# ─── TOOL 1: List pending topics ──────────────────────────────────────────────

@mcp.tool()
def list_pending_topics() -> str:
    """
    List all pending article topics from the review queue.
    These are topics your content pipeline found that Wayzyy doesn't have articles for yet.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.
    """
    import yaml

    topics = []
    if not REVIEW_DIR.exists():
        return "Review queue not found. Make sure 24-7-chronically-online is set up."

    for fname in sorted(REVIEW_DIR.iterdir()):
        if not fname.suffix == ".md":
            continue
        content = fname.read_text()
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1))
                status = fm.get("status", "pending_review")
                if status in ("pending_review", "approved"):
                    topics.append({
                        "keyword": fm.get("keyword", fname.stem),
                        "status": status,
                        "classification": fm.get("classification", ""),
                        "sources": fm.get("source_count", 0),
                    })
            except Exception:
                pass

    if not topics:
        return "No pending topics found. Run the scanner first — say **run the content scanner**."

    approved = [t for t in topics if t["status"] == "approved"]
    pending  = [t for t in topics if t["status"] == "pending_review"]

    lines = [
        f"## Article Queue  —  {len(topics)} topics",
        "",
    ]

    if approved:
        lines.append(f"### ★ Ready to Write  ({len(approved)})")
        lines.append("| # | Topic | Type | Sources |")
        lines.append("|---|-------|------|---------|")
        for i, t in enumerate(approved, 1):
            lines.append(f"| {i} | **{t['keyword']}** | {t['classification']} | {t['sources']} |")
        lines.append("")

    if pending:
        lines.append(f"### ○ Pending Review  ({len(pending)})")
        lines.append("| # | Topic | Type | Sources |")
        lines.append("|---|-------|------|---------|")
        for i, t in enumerate(pending, 1):
            lines.append(f"| {i} | {t['keyword']} | {t['classification']} | {t['sources']} |")
        lines.append("")

    lines.append("---")
    lines.append("Say **write an article about [topic name]** to start writing.")

    return "\n".join(lines)


# ─── TOOL 2: Write article ────────────────────────────────────────────────────

@mcp.tool()
def write_article(topic: str, skip_research: bool = False, extra_research: str = "") -> str:
    """
    Write a complete Wayzyy-style article for a given topic.
    Runs the full pipeline: research → outline → section-by-section writing → style check → saves draft.
    Research is deterministic (fixed Firecrawl searches + one synthesis call, no autonomous
    agent loop) so it's cheap and reliable — no Node.js dependency anymore either.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.

    Args:
        topic: The article topic, e.g. "Tambdi Surla Temple Goa Guide"
        skip_research: Set True to skip Firecrawl research and use model knowledge only (faster)
        extra_research: Paste in your own research/notes/facts here — gets blended into the
                         research brief the writer uses, on top of (or instead of) the automated research.

    Returns:
        Status message with draft path and style check results.
    """
    from agent.researcher import run_research
    from agent.planner import generate_outline
    from agent.writer import parse_outline, write_full_article
    from agent.style_checker import check_article
    from agent.memory_bridge import is_topic_covered, embed_draft

    steps = []
    steps.append(f"Writing article: '{topic}'")

    # Advisory dedup check — doesn't block, just surfaces overlap
    try:
        covered, hits = is_topic_covered(topic)
        if covered:
            steps.append(f"  ⚠ Note: Wayzyy already has something close — \"{hits[0]['title']}\" (similarity {round(hits[0]['score'], 2)}). Consider interlinking instead if this ends up too similar.")
    except Exception as e:
        print(f"[write_article] Dedup check skipped: {e}", file=sys.stderr)

    # Research
    incidental_topics = []
    if not skip_research:
        steps.append("Step 1/4: Researching via Firecrawl + LLM...")
        known_sources = _get_known_sources_for_topic(topic)
        research_result = run_research(topic, known_sources=known_sources)
        research_brief = research_result["brief"]
        incidental_topics = research_result.get("incidental_topics", [])
        steps.append(f"  ✓ Research complete ({'failed — using limited context' if research_result['status'] == 'failed' else 'success'})")
    else:
        steps.append("Step 1/4: Skipping research (using model knowledge)")
        research_brief = f"Topic: {topic}. Write a comprehensive Goa travel guide based on your knowledge of Goa."

    if extra_research.strip():
        research_brief += f"\n\nADDITIONAL RESEARCH PROVIDED BY THE USER (treat as authoritative, prioritize over other sources):\n{extra_research.strip()}"
        steps.append("  ✓ Blended in your provided research")

    # Plan
    steps.append("Step 2/4: Generating outline...")
    outline_text = generate_outline(topic, research_brief)
    steps.append("  ✓ Outline generated")

    # Write
    steps.append("Step 3/4: Writing sections...")
    parsed = parse_outline(outline_text)
    if not parsed["title"]:
        parsed["title"] = topic
    if not parsed["primary_keyword"]:
        parsed["primary_keyword"] = topic

    article = write_full_article(parsed, research_brief)
    steps.append(f"  ✓ Article written (~{len(article.split())} words)")

    # Style check
    steps.append("Step 4/4: Running style check...")
    result = check_article(article)
    article = result["article"]

    # Save
    DRAFTS_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(topic)
    filepath = DRAFTS_DIR / f"{date_str}_{slug}.md"
    filepath.write_text(article)
    steps.append(f"  ✓ Saved to: drafts/{filepath.name}")

    # Embed this draft immediately so future dedup checks see it right away —
    # don't wait for it to eventually get published to the live site.
    try:
        embed_draft(topic, parsed["title"], article, filepath.name)
    except Exception as e:
        print(f"[write_article] Failed to embed draft into memory: {e}", file=sys.stderr)

    # Save any incidental topics research turned up (after dedup check)
    if incidental_topics:
        saved_count = 0
        for it in incidental_topics:
            try:
                it_covered, _ = is_topic_covered(it)
                if not it_covered:
                    _save_incidental_topic(it, origin_topic=topic)
                    saved_count += 1
            except Exception as e:
                print(f"[write_article] Skipping incidental topic '{it}': {e}", file=sys.stderr)
        if saved_count:
            steps.append(f"  ✓ Found {saved_count} new topic idea(s) while researching — added to queue")

    high   = [f for f in result["flags"] if f["severity"] == "HIGH"]
    medium = [f for f in result["flags"] if f["severity"] == "MEDIUM"]
    low    = [f for f in result["flags"] if f["severity"] == "LOW"]

    steps += [
        "",
        f"## Article Written — {topic}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Word count | {result['word_count']:,} |",
        f"| Saved to | `drafts/{filepath.name}` |",
        f"| Must fix | {len(high)} issue(s) |",
        f"| Should fix | {len(medium)} issue(s) |",
        f"| Minor | {len(low)} issue(s) |",
        "",
    ]

    if high:
        steps.append("### Must Fix Before Publishing")
        for f in high:
            steps.append(f"- **{f['type']}** — {f['message']}")
            steps.append(f"  → *{f['action']}*")
        steps.append("")

    if medium:
        steps.append("### Should Fix")
        for f in medium:
            steps.append(f"- **{f['type']}** — {f['message']}")
        steps.append("")

    steps.append("---")
    if high:
        steps.append(f"Fix the issues above, then it's ready. Say **style check {topic}** anytime to re-run.")
    else:
        steps.append("Looking good — do a quick read and publish when ready.")

    return "\n".join(steps)


# ─── TOOL 3: List drafts ─────────────────────────────────────────────────────

@mcp.tool()
def list_drafts() -> str:
    """
    List all saved article drafts.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.
    """
    DRAFTS_DIR.mkdir(exist_ok=True)
    drafts = sorted(DRAFTS_DIR.glob("*.md"), reverse=True)

    if not drafts:
        return "No drafts saved yet. Say **write an article about [topic]** to create one."

    lines = [
        f"## Saved Drafts  —  {len(drafts)} total",
        "",
        "| File | Words | Size | Written |",
        "|------|-------|------|---------|",
    ]
    for d in drafts:
        size_kb = round(d.stat().st_size / 1024, 1)
        word_count = len(d.read_text().split())
        written = datetime.fromtimestamp(d.stat().st_mtime).strftime("%d %b %Y")
        name = d.stem.replace("-", " ").replace("_", " ")
        lines.append(f"| {name} | {word_count:,} | {size_kb}kb | {written} |")

    lines.append("")
    lines.append("---")
    lines.append("Say **show me the [topic] draft** to read one, or **style check [topic]** to review it.")

    return "\n".join(lines)


# ─── TOOL 4: Get draft content ───────────────────────────────────────────────

def _find_draft(filename: str) -> Path | None:
    """Shared fuzzy lookup for a draft file — partial match, then word-by-word."""
    DRAFTS_DIR.mkdir(exist_ok=True)

    matches = list(DRAFTS_DIR.glob(f"*{filename}*"))
    if not matches and filename.endswith(".md"):
        matches = list(DRAFTS_DIR.glob(f"*{filename[:-3]}*"))
    if not matches:
        for word in filename.replace("-", " ").replace("_", " ").split():
            if len(word) > 3:
                matches = list(DRAFTS_DIR.glob(f"*{word}*"))
                if matches:
                    break

    if not matches:
        return None
    return sorted(matches, reverse=True)[0]


@mcp.tool()
def get_draft(filename: str) -> str:
    """
    Read the content of a saved draft.

    Args:
        filename: The draft filename, e.g. "2026-07-26_tambdi-surla-temple-goa-guide.md"
                  (use list_drafts() to see available files)
    """
    filepath = _find_draft(filename)
    if filepath is None:
        return f"Draft not found: {filename}\nUse list_drafts() to see available files."

    content = filepath.read_text()
    word_count = len(content.split())
    return f"Draft: {filepath.name} ({word_count} words)\n\n{content}"


@mcp.tool()
def open_draft(filename: str, app: str = "default") -> str:
    """
    Open a saved draft in a real text editor/app on this Mac, so you can review
    it in an actual window instead of reading it in chat. Runs the real macOS
    `open` command — this opens a local file on your machine, nothing is sent anywhere.

    Args:
        filename: The draft filename or partial match (use list_drafts() to see options)
        app: Which app to open it in — "default" (system default for .md files),
             "antigravity", "textedit", or "finder" (reveals the file instead of opening it)
    """
    import subprocess

    filepath = _find_draft(filename)
    if filepath is None:
        return f"Draft not found: {filename}\nUse list_drafts() to see available files."

    ANTIGRAVITY_CLI = "/Applications/Antigravity IDE.app/Contents/Resources/app/bin/antigravity-ide"
    app_map = {
        "textedit": "TextEdit",
    }

    try:
        if app == "finder":
            subprocess.run(["open", "-R", str(filepath)], check=True)
            action = "Revealed in Finder"
        elif app == "antigravity":
            # Use the real CLI binary (this is a VS Code fork) instead of `open -a` —
            # more reliable about actually opening this specific file in the running window.
            subprocess.run([ANTIGRAVITY_CLI, str(filepath)], check=True)
            action = "Opened in Antigravity IDE (press Cmd+Shift+V there to toggle Markdown Preview and see images rendered)"
        elif app in app_map:
            subprocess.run(["open", "-a", app_map[app], str(filepath)], check=True)
            action = f"Opened in {app_map[app]}"
        else:
            subprocess.run(["open", str(filepath)], check=True)
            action = "Opened in the default app for .md files"
    except subprocess.CalledProcessError as e:
        return f"Failed to open {filepath.name}: {e}"

    return f"{action}: {filepath.name}"


@mcp.tool()
def preview_draft(filename: str = "") -> str:
    """
    Start a local preview server (if not already running) and return a
    localhost URL where the draft renders as an actual HTML page — real
    headings, bold text, and images shown inline, not raw markdown.
    Re-reads the file fresh on every page load, so re-open the URL after
    an edit to see the update. Leave filename blank to get a link to the
    index of all drafts instead of one specific article.

    Args:
        filename: The draft filename or partial match (optional — blank shows all drafts)
    """
    from agent.preview_server import preview_url

    if filename:
        filepath = _find_draft(filename)
        if filepath is None:
            return f"Draft not found: {filename}\nUse list_drafts() to see available files."
        url = preview_url(filepath.stem)
        return f"Preview running at: {url}\n\nOpen that link in your browser — it re-reads the file fresh each time, so refresh after any edits."

    url = preview_url()
    return f"Preview server running at: {url}\n\nOpen that link to see a list of all drafts, or ask for a specific one."


@mcp.tool()
def edit_draft(filename: str, instructions: str) -> str:
    """
    Apply requested changes to an existing saved draft and save the updated version.
    Sends the full article + your instructions to the writer model, which returns the
    complete revised article (not just the changed part) — then re-runs the style check.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it.

    Args:
        filename: The draft filename or partial match (use list_drafts() to see options)
        instructions: What to change, e.g. "make the intro punchier" or "add a section about parking"

    Returns:
        Status message with updated word count and style check results.
    """
    from openai import OpenAI
    from agent.utils import call_with_fallback
    from agent.style_checker import check_article
    from agent.memory_bridge import embed_draft

    filepath = _find_draft(filename)
    if filepath is None:
        return f"Draft not found: {filename}\nUse list_drafts() to see available files."

    original = filepath.read_text()

    prompt = f"""Here is a Wayzyy travel blog article:

---
{original}
---

Requested changes: {instructions}

Rewrite the COMPLETE article with these changes applied. Keep everything else
exactly as it is unless the instructions require changing it. Keep the same
overall structure, headings, and Wayzyy voice/style. Return only the full
revised article, starting with the H1 title."""

    kimi_client = OpenAI(api_key=os.environ["KIMI_API_KEY"], base_url="https://api.moonshot.ai/v1")
    groq_client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    response = call_with_fallback(
        lambda: kimi_client.chat.completions.create(
            model="kimi-k2.7-code-highspeed",
            messages=[{"role": "user", "content": prompt}],
            temperature=1, max_tokens=6000,
        ),
        lambda: groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=2500,
        ),
    )
    revised = response.choices[0].message.content.strip()

    result = check_article(revised)
    revised = result["article"]
    filepath.write_text(revised)

    try:
        embed_draft(filepath.stem, filepath.stem, revised, filepath.name)
    except Exception as e:
        print(f"[edit_draft] Failed to re-embed draft into memory: {e}", file=sys.stderr)

    high = [f for f in result["flags"] if f["severity"] == "HIGH"]
    medium = [f for f in result["flags"] if f["severity"] == "MEDIUM"]

    lines = [
        f"## Draft Updated — {filepath.name}",
        "",
        f"Applied: {instructions}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Word count | {result['word_count']:,} |",
        f"| Must fix | {len(high)} issue(s) |",
        f"| Should fix | {len(medium)} issue(s) |",
        "",
    ]
    if high:
        lines.append("### Must Fix Before Publishing")
        for f in high:
            lines.append(f"- **{f['type']}** — {f['message']}")
    else:
        lines.append("Looking good — say **show me the draft** to review, or **push to github** when ready.")

    return "\n".join(lines)


@mcp.tool()
def save_draft(filename: str, content: str) -> str:
    """
    Save the given text directly as the new content of a draft — no LLM call
    involved. Use this when YOU (the model in this conversation) have already
    composed the fixed/edited article text yourself and just need it written to
    disk — this bypasses Kimi/Groq entirely, so it works even when both are
    rate-limited. Runs the same style check and re-embedding as edit_draft.
    IMPORTANT: Return the tool output exactly as-is — do not summarize or reformat it.

    Args:
        filename: The draft filename or partial match (use list_drafts() to see options)
        content: The complete new article text, starting with the H1 title

    Returns:
        Status message with updated word count and style check results.
    """
    from agent.style_checker import check_article
    from agent.memory_bridge import embed_draft

    filepath = _find_draft(filename)
    if filepath is None:
        return f"Draft not found: {filename}\nUse list_drafts() to see available files."

    result = check_article(content)
    final_text = result["article"]
    filepath.write_text(final_text)

    try:
        embed_draft(filepath.stem, filepath.stem, final_text, filepath.name)
    except Exception as e:
        print(f"[save_draft] Failed to re-embed draft into memory: {e}", file=sys.stderr)

    high = [f for f in result["flags"] if f["severity"] == "HIGH"]
    medium = [f for f in result["flags"] if f["severity"] == "MEDIUM"]

    lines2 = [
        f"## Draft Saved — {filepath.name}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Word count | {result['word_count']:,} |",
        f"| Must fix | {len(high)} issue(s) |",
        f"| Should fix | {len(medium)} issue(s) |",
        "",
    ]
    if high:
        lines2.append("### Must Fix Before Publishing")
        for f in high:
            lines2.append(f"- **{f['type']}** — {f['message']}")
    else:
        lines2.append("Looking good — say **show me the draft** to review, or **push to github** when ready.")

    return "\n".join(lines2)


# The MCP Apps widget approach (view_draft) was removed — Claude Desktop
# doesn't reliably render these yet (confirmed stuck on "Waiting for
# content..." in testing), and having it registered meant the model would
# sometimes pick it over the working get_draft/open_draft tools when asked
# to "open" or "view" a draft. Use get_draft (text in chat) or open_draft
# (real editor window) instead.


# ─── TOOL 5: Style check an existing draft ───────────────────────────────────

@mcp.tool()
def run_style_check(filename: str) -> str:
    """
    Run the 40-point style check on an existing draft and get a report.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.

    Args:
        filename: The draft filename (use list_drafts() to see options)
    """
    from agent.style_checker import check_article

    DRAFTS_DIR.mkdir(exist_ok=True)

    matches = list(DRAFTS_DIR.glob(f"*{filename}*"))
    if not matches:
        for word in filename.replace("-", " ").replace("_", " ").split():
            if len(word) > 3:
                matches = list(DRAFTS_DIR.glob(f"*{word}*"))
                if matches:
                    break
    if not matches:
        return f"Draft not found: {filename}\nUse list_drafts() to see available filenames."

    filepath = sorted(matches, reverse=True)[0]

    content = filepath.read_text()
    result = check_article(content)

    name = filepath.stem.replace("-", " ").replace("_", " ")
    high   = [f for f in result["flags"] if f["severity"] == "HIGH"]
    medium = [f for f in result["flags"] if f["severity"] == "MEDIUM"]
    low    = [f for f in result["flags"] if f["severity"] == "LOW"]

    lines = [
        f"## Style Check — {name}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Word count | {result['word_count']:,} |",
        f"| Auto-fixed | {len(result['fixes_applied'])} issues |",
        f"| Needs review | {len(result['flags'])} flags |",
        "",
    ]

    if not result["flags"]:
        lines.append("**Clean — no issues found. Ready to publish.**")
    else:
        if high:
            lines.append(f"### Must Fix Before Publishing ({len(high)})")
            for f in high:
                lines.append(f"- **{f['type']}** — {f['message']}")
                lines.append(f"  → *{f['action']}*")
            lines.append("")

        if medium:
            lines.append(f"### Should Fix ({len(medium)})")
            for f in medium:
                lines.append(f"- **{f['type']}** — {f['message']}")
                lines.append(f"  → *{f['action']}*")
            lines.append("")

        if low:
            lines.append(f"### Minor ({len(low)})")
            for f in low:
                lines.append(f"- {f['type']} — {f['message']}")
            lines.append("")

    lines.append("---")
    if high:
        lines.append("Fix the **Must Fix** issues above, then it's ready to publish.")
    else:
        lines.append("Looking good — do a quick read and publish when ready.")

    return "\n".join(lines)


@mcp.tool()
def get_pipeline_status() -> str:
    """
    Show the full status of the Wayzyy content pipeline:
    - When the scanner last ran and how many topics it found
    - How many topics are pending vs written
    - How many drafts are saved and when the last one was written
    - What's ready to act on next
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.
    """
    import yaml
    import json

    lines = ["## Wayzyy Content Pipeline", ""]

    # Scanner
    scan_cache = Path(__file__).parent / ".." / "24-7-chronically-online" / "scanner" / "cache" / "last_scan.json"
    if scan_cache.exists():
        scan_time = datetime.fromtimestamp(scan_cache.stat().st_mtime)
        days_ago = (datetime.now() - scan_time).days
        with open(scan_cache) as f:
            scan_data = json.load(f)
        freshness = "fresh" if days_ago < 3 else f"{days_ago} days ago — consider re-running"
        lines += [
            "### Scanner",
            f"| Last Run | Topics Found | Status |",
            f"|----------|--------------|--------|",
            f"| {scan_time.strftime('%d %b %Y, %I:%M %p')} | {len(scan_data)} | {freshness} |",
            "",
        ]
    else:
        lines += ["### Scanner", "Never run — say **run the scanner** to find Goa topics.", ""]

    # Queue
    pending, approved, written = [], [], []
    if REVIEW_DIR.exists():
        for fname in REVIEW_DIR.iterdir():
            if fname.suffix != ".md":
                continue
            content = fname.read_text()
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                try:
                    fm = yaml.safe_load(fm_match.group(1))
                    status = fm.get("status", "pending_review")
                    keyword = fm.get("keyword", fname.stem)
                    if status == "pending_review":
                        pending.append(keyword)
                    elif status == "approved":
                        approved.append(keyword)
                    elif status in ("written", "published"):
                        written.append(keyword)
                except Exception:
                    pass

    lines += [
        "### Queue",
        "| Status | Count | Topics |",
        "|--------|-------|--------|",
        f"| ★ Ready to write | **{len(approved)}** | {', '.join(approved[:3]) or '—'} |",
        f"| ○ Pending review | {len(pending)} | {', '.join(pending[:2]) or '—'}{'...' if len(pending) > 2 else ''} |",
        f"| ✓ Written | {len(written)} | — |",
        "",
    ]

    # Drafts
    DRAFTS_DIR.mkdir(exist_ok=True)
    drafts = sorted(DRAFTS_DIR.glob("*.md"), reverse=True)
    if drafts:
        latest = drafts[0]
        latest_time = datetime.fromtimestamp(latest.stat().st_mtime)
        latest_name = latest.stem.replace("-", " ").replace("_", " ")
        lines += [
            "### Drafts",
            f"| Saved | Latest | Written |",
            f"|-------|--------|---------|",
            f"| {len(drafts)} | {latest_name} | {latest_time.strftime('%d %b %Y')} |",
            "",
        ]
    else:
        lines += ["### Drafts", "None saved yet.", ""]

    # Next action
    lines.append("---")
    lines.append("**What to do next**")
    if approved:
        lines.append(f"→ Say **write an article about {approved[0]}** to start")
    elif pending:
        lines.append(f"→ {len(pending)} topics waiting — say **show my queue** to pick one")
    else:
        lines.append("→ Say **run the scanner** to find new Goa topics")

    return "\n".join(lines)


@mcp.tool()
def run_scanner() -> str:
    """
    Run the content scanner to find new trending Goa topics that Wayzyy doesn't have articles for yet.
    This scans Twitter, Reddit, and the web for trending topics, then checks against existing content.
    Takes 1-2 minutes to complete.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.
    """
    import subprocess

    scanner_dir = Path(__file__).parent / ".." / "24-7-chronically-online"

    result = subprocess.run(
        ["python3", "main.py", "--scan"],
        cwd=scanner_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        return f"Scanner failed:\n{result.stderr[-1000:]}"

    output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
    return f"Scanner complete.\n\n{output}\n\nSay 'what's new in my queue?' to see the updated topic list."


@mcp.tool()
def suggest_next_article() -> str:
    """
    Show every unwritten topic in the queue — what Firecrawl actually found trending
    (real post titles from Twitter/Reddit/web), ranked by relevance to Wayzyy so you
    can review the real evidence and pick which one to write.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it. Render the markdown tables verbatim.
    """
    import yaml

    # Priority keyword signals — higher index = higher priority
    PRIORITY_SIGNALS = [
        # Tier 1 — direct Wayzyy product (booking/villa/stay)
        ["villa booking", "vacation rental", "airbnb alternative", "villas in goa", "where to stay", "villa in goa"],
        # Tier 2 — destination guides that funnel to stays
        ["best beaches", "hidden beaches", "south goa", "north goa vs", "goa itinerary", "workation"],
        # Tier 3 — lifestyle/top of funnel
        ["things to do", "travel guide", "family trip", "budget trip", "monsoon", "restaurants", "nightlife", "scooter"],
    ]
    TIER_LABELS = {3: "Direct Wayzyy product keyword", 2: "Destination guide → drives bookings", 1: "Lifestyle / top-of-funnel", 0: "General"}

    def score_topic(keyword: str) -> int:
        kw = keyword.lower()
        for tier, signals in enumerate(PRIORITY_SIGNALS):
            if any(s in kw for s in signals):
                return len(PRIORITY_SIGNALS) - tier
        return 0

    def extract_sample_signals(body: str, limit: int = 2) -> list[str]:
        """Pull real source titles out of the '## Trend Sources' section."""
        signals = []
        for m in re.finditer(r"^- \[(\w+)\] \[([^\]]+)\]\(([^)]+)\)", body, re.MULTILINE):
            platform, title, _url = m.groups()
            title = title[:70] + ("…" if len(title) > 70 else "")
            signals.append(f"[{platform}] {title}")
            if len(signals) >= limit:
                break
        return signals

    if not REVIEW_DIR.exists():
        return "Review queue not found. Run the scanner first."

    from agent.memory_bridge import is_topic_covered

    candidates = []
    for fname in sorted(REVIEW_DIR.iterdir()):
        if fname.suffix != ".md":
            continue
        content = fname.read_text()
        fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
        if not fm_match:
            continue
        try:
            fm = yaml.safe_load(fm_match.group(1))
            body = fm_match.group(2)
            status = fm.get("status", "pending_review")
            if status in ("written", "published"):
                continue
            keyword = fm.get("keyword", fname.stem)
            # Semantic dedup against published + locally-drafted articles —
            # catches reworded duplicates a substring match would miss
            # (e.g. "villas in Goa" vs "Goa villa rentals").
            try:
                covered, _ = is_topic_covered(keyword)
                if covered:
                    continue
            except Exception as e:
                print(f"[suggest_next_article] Dedup check skipped for '{keyword}': {e}", file=sys.stderr)
            source_count = fm.get("source_count", 0)
            classification = fm.get("classification", "")
            score = score_topic(keyword)
            signals = extract_sample_signals(body)
            candidates.append((score, source_count, keyword, classification, signals))
        except Exception:
            pass

    if not candidates:
        return "No unwritten topics in queue. Say **run the scanner** to find new ones."

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    lines = [
        f"## What to Write Next — {len(candidates)} unwritten topics found by the scanner",
        "",
    ]
    for i, (score, source_count, kw, classification, signals) in enumerate(candidates):
        reason = TIER_LABELS.get(score, "General topic")
        lines.append(f"**{i+1}. {kw}** — {reason} · {source_count} real signals · `{classification}`")
        for s in signals:
            lines.append(f"   - {s}")
        if not signals:
            lines.append("   - (no source titles captured)")
        lines.append("")

    best = candidates[0][2]
    lines += [
        f"**Top pick: \"{best}\"** — highest Wayzyy relevance + most real signals.",
        f"→ Say: **write an article about {best}**",
        "",
        "Or pick any other one from the list above by name.",
    ]

    return "\n".join(lines)


@mcp.tool()
def push_to_github(filename: str) -> str:
    """
    Convert an approved draft into the wayzyy-site repo's real blog post format
    (TSX page, SEO metadata, route, sitemap entry, downloaded hero image), then
    commit everything to a NEW branch and push it. This does NOT push to main
    and does NOT merge anything — it hands back a GitHub compare/PR link for
    you to open and review yourself. Only call this when the user has actually
    said to push — this is a real action on the live site's repo.
    IMPORTANT: Return the tool output exactly as-is — do not summarize, paraphrase, or reformat it.

    Args:
        filename: The draft filename or partial match (use list_drafts() to see options)

    Returns:
        Status message with the PR link to review, or an error if something looks wrong
        (e.g. a slug/file collision) — nothing gets pushed if that happens.
    """
    from agent.site_publisher import publish_draft

    filepath = _find_draft(filename)
    if filepath is None:
        return f"Draft not found: {filename}\nUse list_drafts() to see available files."

    try:
        result = publish_draft(str(filepath), dry_run=False)
    except Exception as e:
        return f"## Push failed — nothing was committed or pushed\n\nError: {e}"

    return (
        f"## Pushed to GitHub — {result['slug']}\n\n"
        f"| | |\n|---|---|\n"
        f"| Branch | `add-blog-{result['slug']}` |\n"
        f"| New page | `src/pages/blog/{result['component_name']}.tsx` |\n"
        f"| Hero image | `{result['hero_image_path']}` |\n\n"
        f"Nothing is live yet — review the actual diff and open the PR here:\n"
        f"{result['pr_url']}"
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
