"""
Mid-write section checker — runs after every H2 is written.
If violations found, injects a fix prompt and rewrites the section once.
This is the "prompt injection" quality gate between sections.
"""

import re
from collections import Counter

BANNED_ADJECTIVES = [
    "stunning", "breathtaking", "beautiful", "serene", "peaceful", "vibrant",
    "picturesque", "magnificent", "gorgeous", "lovely", "amazing", "incredible",
    "wonderful", "fantastic", "perfect", "charming", "quaint", "ideal",
    "holistic", "seamless", "optimal",
]

BANNED_PHRASES = [
    "hidden gem", "hidden gems", "moreover", "furthermore", "additionally",
    "in conclusion", "to summarize", "it is important to note", "needless to say",
    "delve into", "embark on", "tapestry", "at the end of the day",
    "it is worth mentioning", "one should note",
]

PASSIVE_PATTERNS = [
    r"\bcan be \w+ed\b", r"\bis \w+ed by\b", r"\bare \w+ed by\b",
    r"\bwas \w+ed\b", r"\bwere \w+ed\b", r"\bshould be \w+ed\b",
]


def check_section(section_text: str, primary_keyword: str, wayzyy_count: int) -> dict:
    """
    Scan a single written section for violations.
    Returns a violations dict — empty means clean.
    """
    text_lower = section_text.lower()
    violations = {}

    # Check banned adjectives
    adj_hits = {}
    for adj in BANNED_ADJECTIVES:
        count = text_lower.count(adj)
        if count > 0:
            adj_hits[adj] = count
    if adj_hits:
        violations["banned_adjectives"] = adj_hits

    # Check banned phrases
    phrase_hits = [p for p in BANNED_PHRASES if p in text_lower]
    if phrase_hits:
        violations["banned_phrases"] = phrase_hits

    # Check keyword repetition (first word of primary keyword)
    kw = primary_keyword.split()[0].lower()
    kw_count = text_lower.count(kw)
    if kw_count > 3:
        violations["keyword_stuffing"] = {kw: kw_count, "max_allowed": 3}

    # Check Wayzyy overuse in this section
    wayzyy_in_section = text_lower.count("wayzyy")
    if wayzyy_in_section > 1:
        violations["wayzyy_overuse"] = wayzyy_in_section
    if wayzyy_count >= 4 and wayzyy_in_section > 0:
        violations["wayzyy_limit_reached"] = f"Already {wayzyy_count} mentions in article — remove from this section"

    # Check passive voice
    passive_hits = []
    for pattern in PASSIVE_PATTERNS:
        passive_hits.extend(re.findall(pattern, section_text, re.IGNORECASE))
    if len(passive_hits) > 2:
        violations["passive_voice"] = passive_hits[:3]

    # Check word count
    words = len(section_text.split())
    if words > 380:
        violations["too_long"] = f"{words} words — max 350"

    return violations


def build_fix_prompt(section_text: str, violations: dict, section_heading: str, primary_keyword: str) -> str:
    """Build a targeted fix prompt listing exactly what's wrong."""

    fix_instructions = []

    if "banned_adjectives" in violations:
        adj_list = ", ".join([f"'{k}' ×{v}" for k, v in violations["banned_adjectives"].items()])
        fix_instructions.append(
            f"ADJECTIVES TO REPLACE: {adj_list}\n"
            f"Replace each with a specific observation. Example:\n"
            f"  NOT 'ideal for couples' → YES 'works well for couples who want quiet mornings and early sunsets'\n"
            f"  NOT 'peaceful atmosphere' → YES 'on weekday mornings you'll mostly hear birds and the occasional temple bell'\n"
            f"  NOT 'serene surroundings' → YES 'the forest here is dense enough that road noise doesn't reach the courtyard'"
        )

    if "banned_phrases" in violations:
        phrase_list = ", ".join([f"'{p}'" for p in violations["banned_phrases"]])
        fix_instructions.append(
            f"BANNED PHRASES TO REMOVE: {phrase_list}\n"
            f"Rewrite those sentences entirely — don't just swap the phrase."
        )

    if "keyword_stuffing" in violations:
        kw = list(violations["keyword_stuffing"].keys())[0]
        count = violations["keyword_stuffing"][kw]
        fix_instructions.append(
            f"KEYWORD STUFFING: '{kw}' used {count}× in this section (max 3).\n"
            f"Replace excess uses with: 'the temple', 'the site', 'the complex', 'this structure', 'the shrine'"
        )

    if "wayzyy_overuse" in violations or "wayzyy_limit_reached" in violations:
        fix_instructions.append(
            f"WAYZYY OVERUSE: Keep max 1 Wayzyy mention per section, and only if accommodation-relevant.\n"
            f"Remove all but one Wayzyy reference from this section."
        )

    if "passive_voice" in violations:
        examples = ", ".join([f"'{p}'" for p in violations["passive_voice"]])
        fix_instructions.append(
            f"PASSIVE VOICE: Rewrite these to active voice: {examples}"
        )

    if "too_long" in violations:
        fix_instructions.append(
            f"TOO LONG: {violations['too_long']}. Cut the weakest sentences — remove anything that doesn't add new information."
        )

    fixes_str = "\n\n".join(fix_instructions)

    return f"""This section has quality issues that must be fixed before the article can be published.

SECTION TO FIX:
{section_text}

---

SPECIFIC FIXES REQUIRED:
{fixes_str}

---

Rewrite the COMPLETE section fixing ALL of the above issues.
Keep the same H2/H3 structure and all factual content.
Do NOT introduce new banned adjectives or phrases while fixing.
Start directly with: ## {section_heading}
"""
