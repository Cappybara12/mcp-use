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
        return _reddit(topic, keyword, _field(user, "ARTICLE URL", "(blog link)"))
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


def _reddit(topic: str, keyword: str, url: str) -> str:
    return (
        f"<!-- {DEMO_NOTE} -->\n"
        f"### Post 1: lead with an insight\n**Title:** What I learned about {keyword} (and what I got wrong)\n"
        f"**Body:** Two or three honest lessons in plain language, a question for the community, and the full write-up "
        f"linked in a comment: {url}\n\n"
        f"### Post 2: ask a question\n**Title:** How do you approach {keyword}?\n"
        f"**Body:** Share your own approach first, ask for others', and mention you wrote more at {url} (your own blog).\n\n"
        f"### Post 3: a short checklist\n**Title:** A short checklist for {keyword}\n"
        f"**Body:** Five bullet points taken from the article, link in a comment, with disclosure.\n"
    )
