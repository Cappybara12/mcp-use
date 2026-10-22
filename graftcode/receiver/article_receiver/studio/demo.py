"""Offline "demo" AI provider.

It produces clearly labelled template text from the structured briefing lines the pipeline
sends (TOPIC:, PRIMARY KEYWORD:, ...). It is *not* AI: it exists so the whole pipeline, the
SEO check and the review flow can be tried without an API key, and so tests are deterministic.
"""
from __future__ import annotations

import re

DEMO_NOTE = "Demo template text. Choose an AI provider on this node to generate real content."


def _field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"^{re.escape(name)}:[ \t]*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else default


def _title_case(text: str) -> str:
    small = {"a", "an", "and", "the", "of", "to", "in", "for", "on", "vs"}
    words = text.split()
    return " ".join(w if (i and w.lower() in small) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def generate(task: str, system: str, user: str) -> str:
    topic = _field(user, "TOPIC", "your topic")
    keyword = _field(user, "PRIMARY KEYWORD", topic).lower()
    if task == "outline":
        return _outline(topic, keyword)
    if task == "write":
        return _article(topic, keyword, user)
    if task == "reddit":
        return _reddit(topic, keyword, _field(user, "ARTICLE URL", "(blog link)"), user)
    if task == "voice":
        return f"Voice summary ({DEMO_NOTE})\n- Plain, direct sentences.\n- Opens with a concrete problem.\n- Ends with a clear next step."
    return f"{DEMO_NOTE}\n\nTopic: {topic}"


def _outline(topic: str, keyword: str) -> str:
    title = _title_case(f"{keyword}: a practical guide")
    return (
        f"# {title}\n\n"
        f"<!-- {DEMO_NOTE} -->\n"
        "## Why this matters now\n"
        f"## What {keyword} actually involves\n"
        "## A step-by-step approach\n"
        "## Mistakes to avoid\n"
        "## Tools and costs\n"
        "## FAQ\n"
        f"- What is {keyword}?\n- How long does it take?\n- What does it cost?\n- Where should a beginner start?\n"
    )


def _article(topic: str, keyword: str, user: str) -> str:
    opener = _field(user, "OPENER", "question").lower()
    title = _title_case(f"{keyword}: a practical guide")
    hook = {
        "question": f"Have you tried to get started with {keyword} and found advice that does not fit your situation?",
        "statistic": f"Most teams that try {keyword} stop within a month, and the cause is almost never the tool.",
        "story": f"Last spring a small team asked us a simple question about {keyword}, and the honest answer took a page to explain.",
    }.get(opener, f"Getting {keyword} right comes down to a few decisions made early.")
    paragraph = (
        "Start small. Write down what you expect. Then compare it with what happened. "
        "That habit turns guesses into evidence. It keeps the work honest. "
    )
    return (
        f"---\ntitle: \"{title}\"\nprimary_keyword: \"{keyword}\"\ndemo: true\n---\n\n"
        f"# {title}\n\n"
        f"> {DEMO_NOTE}\n\n"
        f"{hook} This guide explains {keyword} in plain language and shows where the real effort goes.\n\n"
        f"## Why {keyword} matters now\n{paragraph * 3}\n\n"
        f"## What {keyword} involves\n{paragraph * 3}\nRead more at https://example.com/guide for background.\n\n"
        f"## A step-by-step approach\n1. Define the goal.\n2. Pick one measure of progress.\n3. Review weekly.\n\n{paragraph * 3}\n\n"
        f"## Mistakes to avoid\n{paragraph * 3}\n\n"
        f"## Tools and costs\n{paragraph * 3}\n\n"
        f"## FAQ\n### What is {keyword}?\nIt is the practice described above, applied to your own situation.\n\n"
        f"### How long does it take?\nPlan for a few weeks before you see a clear signal.\n\n"
        f"### What does it cost?\nThe main cost is time; tools are optional.\n\n"
        f"### Where should a beginner start?\nWith one small goal and a weekly review.\n\n"
        f"Ready to go further? Read the next guide on our blog.\n"
    )


def _reddit(topic: str, keyword: str, url: str, user: str = "") -> str:
    ptype = _field(user, "POST TYPE", "discussion")
    disclosure = _field(user, "DISCLOSURE (put this at the top of every post, word for word)", "")
    competitors = _field(user, "COMPETITORS TO COMPARE", "the alternatives")
    top = f"{disclosure}\n\n" if disclosure else ""
    kw = keyword
    drafts = {
        "discussion": (f"What I learned about {kw} (and what I got wrong)",
                       "Two or three honest lessons in plain language, then: what has your experience been?"),
        "comparison_table": (f"{kw}: how the options compare",
                             "| Option | Best for | Main downside |\n|---|---|---|\n| A | Small teams | Limited reporting |\n| B | Larger teams | Setup time |\n| C | Budget | Fewer features |\n\nWhat surprised me, then a question for the community."),
        "contrarian": (f"Unpopular opinion: the usual advice on {kw} is backwards",
                       "The common belief, my reasoning with evidence from the article, the best counter-argument, and: what have you seen?"),
        "competitor": (f"{kw}: {competitors} compared fairly",
                       f"Only facts I could verify, each linked ({url}). Where the alternatives are better. What I could not verify."),
        "howto": (f"How to approach {kw}, step by step", "The problem, numbered steps, common mistakes. Please correct me where I am wrong."),
        "feedback": (f"Looking for feedback on my {kw} write-up", "What I wrote, the specific thing I want feedback on, and what I am unsure about."),
    }
    title, body = drafts.get(ptype, drafts["discussion"])
    out = f"<!-- {DEMO_NOTE} -->\n"
    for n, (t, b) in enumerate([(title, body), (f"{title} (angle 2)", body)], 1):
        out += f"### Post {n}\n**Title:** {t}\n**Body:**\n{top}{b}\nFull write-up in a comment (my own blog: {url}).\n\n"
    return out
