"""
Style checker — runs the 40-point checklist against the written article.
Auto-fixes what it can, flags the rest for manual review.
"""


import sys
import re
from collections import Counter


AI_PHRASES = [
    "moreover", "furthermore", "additionally", "in conclusion", "to summarize",
    "it is important to note", "it is worth mentioning", "one should note",
    "needless to say", "delve into", "embark on", "tapestry", "nestled",
    "picture-perfect", "hidden gem", "breathtaking", "stunning", "vibrant",
    "in addition to", "as a result", "therefore", "thus", "it goes without saying",
    "without further ado", "at the end of the day", "in today's world",
    "leverage", "paramount", "utilize", "facilitate", "optimal",
    "multifaceted", "holistic", "synergy", "seamlessly",
]

PASSIVE_PATTERNS = [
    r"\bcan be \w+ed\b",
    r"\bis \w+ed by\b",
    r"\bare \w+ed by\b",
    r"\bwas \w+ed by\b",
    r"\bwere \w+ed by\b",
    r"\bshould be \w+ed\b",
    r"\bwill be \w+ed\b",
]

OVERSELL_WORDS = [
    "must-visit", "paradise", "ultimate", "best ever", "perfect",
    "world-class", "unparalleled", "second to none", "one of a kind",
]

BANNED_OPENERS = [
    "in conclusion", "to summarize", "in summary", "to conclude",
    "welcome to", "are you planning", "have you ever wondered",
]


def check_article(article: str) -> dict:
    """Run all style checks. Returns fixes applied and flags for manual review."""

    text = article
    flags = []
    fixes = []

    lines = text.split("\n")
    words = text.lower().split()
    word_count = len(words)

    # --- AUTO-FIXABLE ---

    # Fix: remove double blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", text)
    if cleaned != text:
        text = cleaned
        fixes.append("Removed extra blank lines")

    # Fix: strip trailing whitespace
    cleaned = "\n".join(line.rstrip() for line in text.split("\n"))
    if cleaned != text:
        text = cleaned
        fixes.append("Stripped trailing whitespace")

    # --- FLAGS: AI PHRASES ---
    found_ai = []
    text_lower = text.lower()
    for phrase in AI_PHRASES:
        count = text_lower.count(phrase.lower())
        if count > 0:
            found_ai.append(f"'{phrase}' × {count}")

    if found_ai:
        flags.append({
            "type": "AI_PHRASES",
            "severity": "HIGH",
            "message": f"Found AI-sounding phrases: {', '.join(found_ai)}",
            "action": "Manually rewrite these phrases"
        })

    # --- FLAGS: KEYWORD STUFFING ---
    # Find the primary keyword from H1
    h1_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    if h1_match:
        title_words = h1_match.group(1).lower().split()
        # Check main location word
        if title_words:
            main_word = [w for w in title_words if len(w) > 4 and w not in ("guide", "beach", "honest", "complete")]
            if main_word:
                keyword = main_word[0]
                count = text_lower.count(keyword)
                if count > 12:
                    flags.append({
                        "type": "KEYWORD_STUFFING",
                        "severity": "MEDIUM",
                        "message": f"'{keyword}' appears {count} times — target max 10",
                        "action": "Replace some occurrences with synonyms (the state, the region, the destination, the coastline)"
                    })

    # --- FLAGS: REPEATED ADJECTIVES ---
    adjective_counts = Counter()
    for adj in ["beautiful", "stunning", "breathtaking", "gorgeous", "amazing",
                "incredible", "wonderful", "lovely", "fantastic", "peaceful",
                "serene", "pristine", "perfect", "ideal"]:
        count = text_lower.count(adj)
        if count > 0:
            adjective_counts[adj] = count

    overused = {k: v for k, v in adjective_counts.items() if v > 2}
    if overused:
        flags.append({
            "type": "REPEATED_ADJECTIVES",
            "severity": "MEDIUM",
            "message": f"Overused adjectives: {dict(overused)}",
            "action": "Replace repeated adjectives with specific descriptions"
        })

    # --- FLAGS: PASSIVE VOICE ---
    passive_found = []
    for pattern in PASSIVE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        passive_found.extend(matches)
    if len(passive_found) > 3:
        flags.append({
            "type": "PASSIVE_VOICE",
            "severity": "LOW",
            "message": f"Found {len(passive_found)} passive constructions: {passive_found[:3]}...",
            "action": "Rewrite to active voice where possible"
        })

    # --- FLAGS: OVERSELL WORDS ---
    oversell_found = [w for w in OVERSELL_WORDS if w.lower() in text_lower]
    if oversell_found:
        flags.append({
            "type": "OVERSELLING",
            "severity": "LOW",
            "message": f"Promotional words found: {oversell_found}",
            "action": "Remove or replace unless genuinely justified"
        })

    # --- FLAGS: LONG SECTIONS ---
    h2_sections = re.split(r"\n## ", text)
    long_sections = []
    for section in h2_sections[1:]:
        first_line = section.split("\n")[0].strip()
        section_words = len(section.split())
        if section_words > 400:
            long_sections.append(f"'{first_line}' ({section_words} words)")

    if long_sections:
        flags.append({
            "type": "LONG_SECTIONS",
            "severity": "MEDIUM",
            "message": f"Sections exceeding 400 words: {long_sections}",
            "action": "Break these into more H3 subsections or split the H2"
        })

    # --- FLAGS: DUPLICATE H2s ---
    h2s = re.findall(r"^## (.+)$", text, re.MULTILINE)
    h2_counter = Counter(h2s)
    dupes = {k: v for k, v in h2_counter.items() if v > 1}
    if dupes:
        flags.append({
            "type": "DUPLICATE_H2",
            "severity": "HIGH",
            "message": f"Duplicate H2 headings: {list(dupes.keys())}",
            "action": "Remove or rename duplicate sections"
        })

    # --- FLAGS: BANNED CONCLUSION OPENERS ---
    paragraphs = [p.strip().lower() for p in text.split("\n\n") if p.strip()]
    last_para = paragraphs[-1] if paragraphs else ""
    for opener in BANNED_OPENERS:
        if last_para.startswith(opener):
            flags.append({
                "type": "GENERIC_CONCLUSION",
                "severity": "MEDIUM",
                "message": f"Conclusion starts with banned phrase: '{opener}'",
                "action": "Rewrite conclusion to end with a recommendation or honest opinion"
            })

    # --- FLAGS: WAYZYY MENTION CHECK ---
    wayzyy_count = text_lower.count("wayzyy")
    if wayzyy_count < 3:
        flags.append({
            "type": "WAYZYY_MENTIONS",
            "severity": "LOW",
            "message": f"Only {wayzyy_count} Wayzyy mentions found (target: 3-5)",
            "action": "Add natural Wayzyy mentions in accommodation sections"
        })
    elif wayzyy_count > 6:
        flags.append({
            "type": "WAYZYY_OVERUSE",
            "severity": "MEDIUM",
            "message": f"{wayzyy_count} Wayzyy mentions — may feel promotional",
            "action": "Reduce to 4-5 mentions max"
        })

    # --- FLAGS: WORD COUNT ---
    if word_count < 2000:
        flags.append({
            "type": "WORD_COUNT",
            "severity": "HIGH",
            "message": f"Article is only {word_count} words — target 3,000+",
            "action": "Expand thin sections with more practical detail"
        })
    elif word_count > 6000:
        flags.append({
            "type": "WORD_COUNT",
            "severity": "LOW",
            "message": f"Article is {word_count} words — consider trimming fluff",
            "action": "Review for repetition and remove any duplicate information"
        })

    return {
        "article": text,
        "word_count": word_count,
        "fixes_applied": fixes,
        "flags": flags,
    }


def print_style_report(result: dict):
    """Print a clean style check report."""
    print("\n" + "="*60, file=sys.stderr)
    print("STYLE CHECK REPORT", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Word count: {result['word_count']}", file=sys.stderr)

    if result["fixes_applied"]:
        print(f"\n✓ Auto-fixed ({len(result['fixes_applied'])}):", file=sys.stderr)
        for fix in result["fixes_applied"]:
            print(f"  • {fix}", file=sys.stderr)

    if result["flags"]:
        high = [f for f in result["flags"] if f["severity"] == "HIGH"]
        medium = [f for f in result["flags"] if f["severity"] == "MEDIUM"]
        low = [f for f in result["flags"] if f["severity"] == "LOW"]

        if high:
            print(f"\n🔴 HIGH priority ({len(high)}):", file=sys.stderr)
            for f in high:
                print(f"  [{f['type']}] {f['message']}", file=sys.stderr)
                print(f"    → {f['action']}", file=sys.stderr)

        if medium:
            print(f"\n🟡 MEDIUM priority ({len(medium)}):", file=sys.stderr)
            for f in medium:
                print(f"  [{f['type']}] {f['message']}", file=sys.stderr)
                print(f"    → {f['action']}", file=sys.stderr)

        if low:
            print(f"\n🟢 LOW priority ({len(low)}):", file=sys.stderr)
            for f in low:
                print(f"  [{f['type']}] {f['message']}", file=sys.stderr)
    else:
        print("\n✓ No issues found — article looks clean!", file=sys.stderr)

    print("="*60, file=sys.stderr)
