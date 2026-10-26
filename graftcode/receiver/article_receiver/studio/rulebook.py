"""Learn a blog's writing habits from existing posts and turn them into an editable rulebook.

Everything here is measured, not guessed: each learned rule carries the evidence it came from
(for example "11 of 14 posts (79%)"), and the same rules are used to check new drafts.
"""
from __future__ import annotations

import math
import re
import statistics
import uuid
from collections import Counter

from .docs import words_in

EM_DASH = "—"
_STOP = set("""a an and are as at be but by for from has have how i in is it its of on or our so that the their this to was we what when where which who why will with you your""".split())
_HOOK_WORDS = re.compile(r"\b(most|never|stop|wrong|mistake|secret|truth|myth|honest|why|nobody)\b", re.I)
_CTA = re.compile(r"\b(book|try|start|get started|read|contact|subscribe|download|learn more|sign up|join|talk to|see how|explore|check out)\b", re.I)
_STORY = re.compile(r"^(i|we|last|when i|when we|yesterday|one |a few |years ago|my )\b", re.I)
_DIRECT = re.compile(r"^(you|if you|your|are you|do you)\b", re.I)


# ── measuring one post ────────────────────────────────────────────────────────

def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“(])", text.strip())
    return [p for p in parts if p.strip()]


def _syllables(word: str) -> int:
    word = word.lower()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1
    return max(1, count)


def flesch(text: str) -> float:
    words = re.findall(r"[A-Za-z']+", text)
    sents = _sentences(text) or [text]
    if not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    return round(206.835 - 1.015 * (len(words) / max(1, len(sents))) - 84.6 * (syl / len(words)), 1)


def opener_type(first_paragraph: str) -> str:
    sentence = (_sentences(first_paragraph) or [first_paragraph])[0].strip()
    if sentence.endswith("?"):
        return "question"
    if _DIRECT.match(sentence):
        return "direct"
    if _STORY.match(sentence):
        return "story"
    if re.search(r"\d", sentence):
        return "statistic"
    return "claim"


def has_hook(first_paragraph: str) -> bool:
    intro = " ".join(first_paragraph.split()[:120])
    return bool(re.search(r"\d", intro) or "?" in intro or _HOOK_WORDS.search(intro))


def title_traits(title: str) -> dict:
    return {
        "chars": len(title), "has_number": bool(re.search(r"\b\d+\b", title)),
        "has_year": bool(re.search(r"\b20\d\d\b", title)), "has_colon": ":" in title,
        "is_question": title.strip().endswith("?"), "how_to": title.lower().startswith("how to"),
    }


def analyze_post(doc: dict, url: str = "") -> dict:
    text = doc["text"]
    words = max(1, doc["words"])
    paragraphs = doc["paragraphs"]
    first = next((p for p in paragraphs if words_in(p) >= 8), paragraphs[0] if paragraphs else "")
    last = paragraphs[-1] if paragraphs else ""
    sents = _sentences(text)
    h2 = sum(1 for lvl, _ in doc["headings"] if lvl == 2)
    h3 = sum(1 for lvl, _ in doc["headings"] if lvl == 3)
    question_heads = sum(1 for lvl, t in doc["headings"] if lvl in (2, 3) and t.strip().endswith("?"))
    return {
        "url": url, "title": doc["title"], "words": doc["words"],
        "title_traits": title_traits(doc["title"]),
        "em_dash_per_1000": round(text.count(EM_DASH) / words * 1000, 2),
        "opener": opener_type(first) if first else "claim", "hook": has_hook(first) if first else False,
        "h2": h2, "h3": h3, "question_headings": question_heads,
        "avg_sentence_words": round(sum(words_in(s) for s in sents) / max(1, len(sents)), 1),
        "avg_paragraph_words": round(sum(words_in(p) for p in paragraphs) / max(1, len(paragraphs)), 1),
        "lists": doc["lists"], "bold": doc["bold"], "images": doc["images"], "tables": doc.get("tables", 0),
        "external_links": doc["external_links"], "internal_links": doc["internal_links"],
        "faq_pairs": len(doc["faq_pairs"]), "faq_heading": doc["has_faq_heading"], "faq_schema": doc["has_faq_schema"],
        "cta": bool(_CTA.search(last)), "reading_ease": flesch(text),
    }


# ── learning from many posts ──────────────────────────────────────────────────

def _share(posts: list[dict], pred) -> tuple[int, float]:
    n = sum(1 for p in posts if pred(p))
    return n, (n / len(posts) if posts else 0.0)


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _quantile(values: list[float], q: float) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _signature_phrases(texts: list[str], min_docs: int) -> list[str]:
    """Three-word phrases that recur across several posts (a blog's verbal habits)."""
    seen: Counter = Counter()
    for text in texts:
        words = re.findall(r"[a-z']+", text.lower())
        grams = {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}
        for g in grams:
            seen[g] += 1
    out = []
    for gram, n in seen.most_common(400):
        parts = gram.split()
        if n >= min_docs and sum(1 for w in parts if w not in _STOP) >= 2:
            out.append(gram)
        if len(out) >= 8:
            break
    return out


def learn(posts: list[dict], texts: list[str] | None = None) -> dict:
    """Aggregate per-post measurements into stats and a list of learned rules."""
    n = len(posts)
    if not n:
        return {"stats": {}, "rules": []}
    words = [p["words"] for p in posts]
    em = [p["em_dash_per_1000"] for p in posts]
    stats = {
        "posts": n, "median_words": int(statistics.median(words)), "p25_words": int(_quantile(words, 0.25)),
        "p75_words": int(_quantile(words, 0.75)), "mean_em_dash_per_1000": round(statistics.mean(em), 2),
        "median_h2": int(statistics.median([p["h2"] for p in posts])),
        "median_sentence_words": round(statistics.median([p["avg_sentence_words"] for p in posts]), 1),
        "median_reading_ease": round(statistics.median([p["reading_ease"] for p in posts]), 1),
        "median_external_links": int(statistics.median([p["external_links"] for p in posts])),
        "median_bold": int(statistics.median([p["bold"] for p in posts])),
        "median_title_chars": int(statistics.median([p["title_traits"]["chars"] for p in posts])),
        "openers": dict(Counter(p["opener"] for p in posts)),
    }
    rules: list[dict] = []

    def add(rule_id, kind, text, evidence, params=None):
        rules.append({"id": rule_id, "kind": kind, "text": text, "evidence": evidence, "params": params or {},
                      "enabled": True, "source": "learned"})

    lo = int(stats["p25_words"] * 0.85)
    hi = int(stats["p75_words"] * 1.15)
    add("length", "length", f"Aim for about {stats['median_words']} words (typically {lo} to {hi}).",
        f"Median of {n} posts is {stats['median_words']} words.", {"min": lo, "max": hi, "target": stats["median_words"]})

    mean_em = stats["mean_em_dash_per_1000"]
    if mean_em < 0.5:
        add("em_dash", "em_dash", "Do not use em dashes. Use a comma, a full stop or a colon instead.",
            f"{mean_em} em dashes per 1,000 words across {n} posts.", {"max_per_1000": 0.5})
    else:
        cap = math.ceil(mean_em * 1.5)
        add("em_dash", "em_dash", f"Em dashes are part of this voice; keep them under {cap} per 1,000 words.",
            f"{mean_em} em dashes per 1,000 words on average.", {"max_per_1000": cap})

    top, top_n = max(stats["openers"].items(), key=lambda kv: kv[1])
    allowed = [k for k, v in stats["openers"].items() if v / n >= 0.25] or [top]
    names = {"question": "a direct question", "statistic": "a number or statistic", "story": "a short personal story",
             "direct": "a sentence that speaks to the reader", "claim": "a clear claim"}
    add("opener", "opener", f"Open with {names[top]}" + (f" (also fine: {', '.join(names[a] for a in allowed if a != top)})" if len(allowed) > 1 else "") + ".",
        f"{top_n} of {n} posts ({_pct(top_n / n)}) open this way.", {"allowed": allowed})

    hook_n, hook_p = _share(posts, lambda p: p["hook"])
    if hook_p >= 0.5:
        add("hook", "hook", "Put a hook in the first 100 words: a number, a question or a bold claim.",
            f"{hook_n} of {n} posts ({_pct(hook_p)}) do.", {})

    faq_n, faq_p = _share(posts, lambda p: p["faq_pairs"] >= 2 or p["faq_heading"])
    schema_n, schema_p = _share(posts, lambda p: p["faq_schema"])
    if faq_p >= 0.4:
        pairs = [p["faq_pairs"] for p in posts if p["faq_pairs"]]
        min_pairs = max(2, int(statistics.median(pairs))) if pairs else 3
        add("faq", "faq", f"End with an FAQ of at least {min_pairs} questions" + (" and publish it as FAQPage JSON-LD schema." if schema_p >= 0.4 else "."),
            f"{faq_n} of {n} posts ({_pct(faq_p)}) have an FAQ; {schema_n} publish FAQPage schema.",
            {"min_pairs": min_pairs, "schema": schema_p >= 0.4})

    q_n, q_p = _share(posts, lambda p: p["question_headings"] >= 1)
    add("structure", "structure", f"Use about {stats['median_h2']} H2 sections" + ("; phrase some headings as questions." if q_p >= 0.4 else "."),
        f"Median {stats['median_h2']} H2s; {q_n} of {n} posts ({_pct(q_p)}) use question headings.",
        {"h2_min": max(2, stats["median_h2"] - 2), "h2_max": stats["median_h2"] + 4})

    t = [p["title_traits"] for p in posts]
    num_n = sum(x["has_number"] for x in t)
    year_n = sum(x["has_year"] for x in t)
    col_n = sum(x["has_colon"] for x in t)
    bits = []
    if num_n / n >= 0.3:
        bits.append("a number")
    if year_n / n >= 0.3:
        bits.append("the year")
    if col_n / n >= 0.3:
        bits.append("a colon (topic: promise)")
    add("title", "title", f"Titles stay under {int(_quantile([x['chars'] for x in t], 0.9)) + 5} characters" + (f" and often include {', '.join(bits)}." if bits else "."),
        f"Median title is {stats['median_title_chars']} characters; numbers in {_pct(num_n / n)}, year in {_pct(year_n / n)}, colon in {_pct(col_n / n)}.",
        {"max_chars": int(_quantile([x["chars"] for x in t], 0.9)) + 5})

    add("sentences", "sentences", f"Keep sentences short: about {stats['median_sentence_words']} words on average.",
        f"Median average sentence length is {stats['median_sentence_words']} words; reading ease {stats['median_reading_ease']}.",
        {"max_avg_words": math.ceil(stats["median_sentence_words"] * 1.35)})

    list_n, list_p = _share(posts, lambda p: p["lists"] >= 1)
    if list_p >= 0.5:
        add("lists", "lists", f"Use bullet or numbered lists; bold key terms sparingly (about {stats['median_bold']} per post).",
            f"{list_n} of {n} posts ({_pct(list_p)}) use lists.", {})

    if stats["median_external_links"] >= 1:
        add("links", "links", f"Cite sources: about {stats['median_external_links']} external link{'s' if stats['median_external_links'] != 1 else ''} per post.",
            f"Median {stats['median_external_links']} external links.", {"min_external": max(1, stats["median_external_links"] - 1)})

    tab_n, tab_p = _share(posts, lambda p: p.get("tables", 0) >= 1)
    if tab_p >= 0.3:
        each = statistics.median([p["tables"] for p in posts if p.get("tables", 0) >= 1])
        add("tables", "note", "Add a comparison table when you compare 3 or more options across several attributes; otherwise write prose "
            f"(about {int(each)} per post when one is used).", f"{tab_n} of {n} posts ({_pct(tab_p)}) include a table.", {})

    cta_n, cta_p = _share(posts, lambda p: p["cta"])
    if cta_p >= 0.5:
        add("cta", "cta", "Finish with a clear next step for the reader.", f"{cta_n} of {n} posts ({_pct(cta_p)}) do.", {})

    if texts and n >= 3:
        phrases = _signature_phrases(texts, max(2, n // 2))
        if phrases:
            add("signature", "note", "Phrases that recur in this voice (use naturally, never force): " + "; ".join(phrases[:6]) + ".",
                f"Each appears in at least {max(2, n // 2)} posts.", {})
    return {"stats": stats, "rules": rules}


# ── merging with what the person has edited ───────────────────────────────────

def merge_rulebook(existing: dict, learned: dict, sources: list[dict]) -> dict:
    """Refresh learned rules but keep the person's choices: disabled rules, edited text and custom rules."""
    old = {r["id"]: r for r in existing.get("rules", [])}
    merged: list[dict] = []
    for rule in learned["rules"]:
        prev = old.pop(rule["id"], None)
        if prev:
            rule["enabled"] = prev.get("enabled", True)
            if prev.get("edited"):
                rule["text"], rule["edited"] = prev["text"], True
        merged.append(rule)
    merged.extend(r for r in old.values() if r.get("source") == "custom")
    from .store import now_iso
    return {"rules": merged, "stats": learned["stats"], "sources": sources[:50], "updated_at": now_iso()}


def new_custom_rule(text: str, kind: str = "note", params: dict | None = None) -> dict:
    return {"id": "custom-" + uuid.uuid4().hex[:8], "kind": kind, "text": text.strip()[:600], "evidence": "Added by you.",
            "params": params or {}, "enabled": True, "source": "custom"}


def rules_prompt(rulebook: dict) -> str:
    rules = [r for r in rulebook.get("rules", []) if r.get("enabled", True)]
    if not rules:
        return ""
    return "WRITING RULEBOOK (follow every rule):\n" + "\n".join(f"- {r['text']}" for r in rules)


# ── checking a draft against the rulebook ─────────────────────────────────────

def check_rules(doc: dict, rulebook: dict) -> list[dict]:
    """Return one result per enabled rule that can be checked mechanically."""
    post = analyze_post(doc)
    out = []
    for rule in rulebook.get("rules", []):
        if not rule.get("enabled", True):
            continue
        k, p = rule.get("kind"), rule.get("params", {})
        ok, detail = None, ""
        if k == "length":
            ok = p["min"] <= post["words"] <= p["max"]
            detail = f"{post['words']} words (target {p['min']} to {p['max']})"
        elif k == "em_dash":
            ok = post["em_dash_per_1000"] <= p["max_per_1000"]
            detail = f"{post['em_dash_per_1000']} per 1,000 words (limit {p['max_per_1000']})"
        elif k == "opener":
            ok = post["opener"] in p["allowed"]
            detail = f"opens with a {post['opener']}"
        elif k == "hook":
            ok, detail = post["hook"], "hook found" if post["hook"] else "no hook in the first 100 words"
        elif k == "faq":
            ok = post["faq_pairs"] >= p["min_pairs"]   # the JSON-LD schema itself is generated by the SEO check
            detail = f"{post['faq_pairs']} FAQ questions (need {p['min_pairs']})"
        elif k == "structure":
            ok = p["h2_min"] <= post["h2"] <= p["h2_max"]
            detail = f"{post['h2']} H2 sections (target {p['h2_min']} to {p['h2_max']})"
        elif k == "title":
            ok = post["title_traits"]["chars"] <= p["max_chars"]
            detail = f"title is {post['title_traits']['chars']} characters (limit {p['max_chars']})"
        elif k == "sentences":
            ok = post["avg_sentence_words"] <= p["max_avg_words"]
            detail = f"sentences average {post['avg_sentence_words']} words (limit {p['max_avg_words']})"
        elif k == "links":
            ok = post["external_links"] >= p["min_external"]
            detail = f"{post['external_links']} external links (need {p['min_external']})"
        elif k == "cta":
            ok, detail = post["cta"], "ends with a next step" if post["cta"] else "no call to action at the end"
        elif k == "banned_phrases":
            text = doc["text"].lower() + " " + doc["title"].lower()
            hits = [ph for ph in p.get("phrases", []) if ph.lower() in text]
            ok, detail = not hits, ("found: " + ", ".join(hits)) if hits else "none found"
        if ok is not None:
            out.append({"rule_id": rule["id"], "text": rule["text"], "ok": bool(ok), "detail": detail})
    return out
