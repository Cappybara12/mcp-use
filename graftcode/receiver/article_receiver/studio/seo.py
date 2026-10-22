"""Deterministic SEO checks for a draft, plus FAQ schema and metadata generation."""
from __future__ import annotations

import json
import math
import re

from .docs import parse_markdown, words_in
from .rulebook import check_rules


def slugify(text: str, limit: int = 70) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].strip("-") or "post"


def faq_jsonld(pairs: list[tuple[str, str]]) -> dict | None:
    pairs = [(q, a) for q, a in pairs if q.strip() and a.strip()]
    if not pairs:
        return None
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q.strip(),
                        "acceptedAnswer": {"@type": "Answer", "text": a.strip()}} for q, a in pairs],
    }


def meta_description(doc: dict, front: dict) -> str:
    if front.get("description"):
        return front["description"][:160]
    first = next((p for p in doc["paragraphs"] if words_in(p) >= 8), "")
    first = re.sub(r"\s+", " ", first).strip()
    if len(first) <= 155:
        return first
    cut = first[:155].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "..."


def _front_matter(markdown: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", markdown, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if v.strip():
                out[k.strip().lower()] = v.strip().strip("\"'")
    return out


def check(markdown: str, keyword: str, rulebook: dict, site_url: str = "") -> dict:
    front = _front_matter(markdown)
    doc = parse_markdown(markdown, site_url)
    keyword = (keyword or front.get("primary_keyword") or "").strip().lower()
    text_l = doc["text"].lower()
    title = doc["title"]
    total_words = max(1, doc["words"])
    checks: list[dict] = []

    def add(cid, label, ok, detail, severity="warn", fix=""):
        checks.append({"id": cid, "label": label, "ok": bool(ok), "detail": detail,
                       "severity": severity if not ok else "pass", "fix": "" if ok else fix})

    h1s = [t for lvl, t in doc["headings"] if lvl == 1]
    h2s = [t for lvl, t in doc["headings"] if lvl == 2]
    add("h1", "One H1 title", len(h1s) == 1, f"{len(h1s)} H1 headings", "error", "Use exactly one # heading as the title.")
    add("title_len", "Title is 60 characters or fewer", len(title) <= 60, f"{len(title)} characters", "warn",
        "Shorten the title so it is not cut off in search results.")
    add("h2s", "At least 3 H2 sections", len(h2s) >= 3, f"{len(h2s)} H2 sections", "warn", "Break the article into more sections.")

    uses = 0
    if keyword:
        uses = len(re.findall(rf"\b{re.escape(keyword)}\b", text_l))
        density = uses / total_words * 100          # phrase occurrences per 100 words
        first100 = " ".join(text_l.split()[:100])
        add("kw_title", "Keyword in the title", keyword in title.lower(), f"'{keyword}'", "error", f"Put '{keyword}' in the title.")
        add("kw_intro", "Keyword in the first 100 words", keyword in first100, "", "warn", f"Mention '{keyword}' in the opening paragraph.")
        add("kw_h2", "Keyword in at least one H2", any(keyword in h.lower() for h in h2s), "", "warn", f"Use '{keyword}' in a section heading.")
        add("kw_density", "Keyword used naturally (0.3% to 2.5%)", 0.3 <= density <= 2.5,
            f"{uses} uses, {density:.1f}% of the words", "warn" if density < 0.3 else "error",
            "Use the keyword a little more." if density < 0.3 else "The keyword is overused; vary the wording.")
    else:
        add("kw_missing", "A primary keyword is set", False, "No keyword was given for this article", "warn",
            "Add a keyword in the Keywords step or the plan item.")

    meta = meta_description(doc, front)
    add("meta", "Meta description 70 to 160 characters", 70 <= len(meta) <= 160, f"{len(meta)} characters", "warn",
        "Add a 'description:' line to the front matter, or make the first paragraph a clear summary.")
    add("ext_links", "Cites at least one external source", doc["external_links"] >= 1, f"{doc['external_links']} external links",
        "warn", "Link to a source for any factual claim.")
    if site_url:
        add("int_links", "Links to another page on the site", doc["internal_links"] >= 1, f"{doc['internal_links']} internal links",
            "warn", "Link to a related post on your own site.")
    if not any(r.get("kind") == "length" and r.get("enabled", True) for r in rulebook.get("rules", [])):
        add("words", "At least 600 words", doc["words"] >= 600, f"{doc['words']} words", "warn", "Add depth: examples, steps or data.")

    faq = faq_jsonld(doc["faq_pairs"])
    add("faq", "FAQ section with 3 or more questions", len(doc["faq_pairs"]) >= 3, f"{len(doc['faq_pairs'])} questions found", "warn",
        "Add an '## FAQ' section with '### Question?' headings, each followed by an answer.")

    rules = check_rules(doc, rulebook)
    for r in rules:
        if not r["ok"]:
            checks.append({"id": "rule-" + r["rule_id"], "label": "Rulebook: " + r["text"], "ok": False, "detail": r["detail"],
                           "severity": "warn", "fix": "Revise the draft to follow this rule."})

    penalty = sum(10 if c["severity"] == "error" else 5 for c in checks if not c["ok"])
    script = ""
    if faq:
        script = '<script type="application/ld+json">\n' + json.dumps(faq, indent=2, ensure_ascii=False) + "\n</script>"
    return {
        "score": max(0, 100 - penalty), "checks": checks, "rules": rules, "keyword": keyword,
        "keyword_uses": uses, "words": doc["words"], "title": title, "slug": slugify(front.get("slug") or title),
        "meta_description": meta, "faq_schema": faq, "faq_script": script,
        "headings": [{"level": lvl, "text": t} for lvl, t in doc["headings"]],
    }


def opportunity(item: dict) -> float:
    """Rank a keyword: more searches and lower difficulty is better; informational intent gets a small boost."""
    volume = max(0, item.get("volume") or 0)
    difficulty = item.get("difficulty")
    difficulty = 50 if difficulty is None else max(0, min(100, difficulty))
    score = math.log10(volume + 1) * (100 - difficulty) / 100
    if item.get("intent") == "informational":
        score *= 1.15
    return round(score, 3)
