"""
Planner — takes research brief and generates a Wayzyy-format outline.
Uses Gemini Flash (fast + free). Shows outline for user approval before writing.
"""

import sys
import os
from langchain_openai import ChatOpenAI
from prompts.article_format import (
    BEACH_GUIDE_FORMAT,
    DESTINATION_GUIDE_FORMAT,
    ACCOMMODATION_GUIDE_FORMAT,
    TITLE_PATTERNS,
    INTRO_PATTERNS,
    FAQ_GUIDELINES,
)


PLANNER_PROMPT = """
You are planning a travel article for Wayzyy — a Goa vacation rental platform.

TOPIC: {topic}
ARTICLE TYPE: {article_type}

RESEARCH BRIEF:
{research_brief}

---

EXISTING WAYZYY ARTICLES (avoid duplicating these):
{existing_articles}

---

Your job: create a detailed article outline in the EXACT Wayzyy format.

TITLE: Pick from these patterns and make it specific:
{title_patterns}

INTRO APPROACH: Choose one of these and describe how the intro will open:
{intro_patterns}

H2 OUTLINE: Follow this format as a base, adapting to what the research shows people actually need:
{format_guide}

RULES FOR THE OUTLINE:
- Target total article length: ~1200 words — keep the outline compact, not exhaustive
- Exactly 4-5 H2 sections total (not more) — pick the most important angles only
- Every H2 must answer ONE specific question
- H2 titles must be conversational, not generic ("What Tambdi Surla Temple Is Actually Like" not "Overview")
- Include one comparison or practical-info section (costs, timings, who it's NOT for — pick what matters most for this topic)
- FAQ section at the end — exactly 3-4 of the most important ACTUAL questions from research, not a long list
- Use gaps from research to sharpen sections, not to add more of them

OUTPUT FORMAT (use exactly this):
---
TITLE: [full article title]
META DESCRIPTION: [155 chars max, includes primary keyword]
PRIMARY KEYWORD: [exact keyword]
SECONDARY KEYWORDS: [3-5 LSI keywords]
ESTIMATED WORD COUNT: ~1200
ARTICLE TYPE: [Beach Guide / Destination Guide / Accommodation Guide / Travel Guide]
WAYZYY MENTION SPOTS: [list which H2 sections are natural spots for Wayzyy mentions]

INTRO APPROACH:
[2-3 sentences describing how the intro will open and what angle it takes]

OUTLINE:
H2: [title]
  H3: [title]
  H3: [title]
  H3: [title]

H2: [title]
  H3: [title]
  ...

FAQ QUESTIONS (from research):
1. [question]
2. [question]
...

INTERNAL LINK OPPORTUNITIES:
- Link to [Wayzyy article title] in [H2 section name]
- ...

CONTENT GAPS WE'RE FILLING:
- [what this article covers that no competitor does]
- ...
---
"""

ARTICLE_TYPES = {
    "beach": BEACH_GUIDE_FORMAT,
    "destination": DESTINATION_GUIDE_FORMAT,
    "accommodation": ACCOMMODATION_GUIDE_FORMAT,
}


def detect_article_type(topic: str) -> tuple[str, str]:
    """Detect article type from topic."""
    topic_lower = topic.lower()

    if any(w in topic_lower for w in ["beach", "coast", "shore", "bay"]):
        return "beach", BEACH_GUIDE_FORMAT
    elif any(w in topic_lower for w in ["villa", "stay", "accommodation", "homestay", "rental", "airbnb"]):
        return "accommodation", ACCOMMODATION_GUIDE_FORMAT
    else:
        return "destination", DESTINATION_GUIDE_FORMAT


def generate_outline(topic: str, research_brief: str, existing_articles: list[str] = None) -> str:
    """Generate a Wayzyy-format outline from research."""

    print(f"\n[planner] Generating outline for: {topic}", file=sys.stderr)

    llm = ChatOpenAI(
        model="kimi-k2.7-code-highspeed",
        api_key=os.environ["KIMI_API_KEY"],
        base_url="https://api.moonshot.ai/v1",
        temperature=1,
        max_tokens=6000,
    )
    fallback_llm = ChatOpenAI(
        model="llama-3.3-70b-versatile",
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3,
        max_tokens=2000,
    )

    article_type, format_guide = detect_article_type(topic)

    existing_str = "\n".join(existing_articles) if existing_articles else "None loaded"

    prompt = PLANNER_PROMPT.format(
        topic=topic,
        article_type=article_type,
        research_brief=research_brief,
        existing_articles=existing_str,
        title_patterns="\n".join(TITLE_PATTERNS),
        intro_patterns=INTRO_PATTERNS,
        format_guide=format_guide,
    )

    from agent.utils import call_with_fallback
    response = call_with_fallback(lambda: llm.invoke(prompt), lambda: fallback_llm.invoke(prompt))
    outline = response.content

    print("[planner] Outline generated.", file=sys.stderr)
    return outline


def show_and_confirm_outline(outline: str) -> str:
    """Show outline to user, allow edits, return confirmed outline."""

    print("\n" + "="*60, file=sys.stderr)
    print("GENERATED OUTLINE — Review before writing starts", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(outline, file=sys.stderr)
    print("="*60, file=sys.stderr)

    print("\nOptions:", file=sys.stderr)
    print("  [enter]  Accept this outline and start writing", file=sys.stderr)
    print("  [e]      Edit the outline manually", file=sys.stderr)
    print("  [r]      Regenerate outline", file=sys.stderr)
    print("  [q]      Quit", file=sys.stderr)

    choice = input("\nYour choice: ").strip().lower()

    if choice == "":
        return outline
    elif choice == "e":
        print("\nPaste your edited outline (press Ctrl+D when done):", file=sys.stderr)
        import sys
        edited = sys.stdin.read()
        return edited.strip()
    elif choice == "r":
        return None  # signal to regenerate
    elif choice == "q":
        raise SystemExit("Aborted by user.")
    else:
        return outline
