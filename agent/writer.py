"""
Writer — takes approved outline + research brief and writes the article
section by section using DeepSeek V3. One LLM call per H2 section.
"""


import sys
import os
import re
from openai import OpenAI
from prompts.style_guide import STYLE_GUIDE_SYSTEM_PROMPT
from agent.utils import with_retry, call_with_fallback
from agent.section_checker import check_section, build_fix_prompt
from agent.config import load_config

_brand = load_config()["brand"]


SECTION_WRITER_PROMPT = """
You are writing one section of a Goa travel article for Wayzyy.

ARTICLE TITLE: {title}
PRIMARY KEYWORD: {primary_keyword}
SECTION TO WRITE: {section_heading} (H2)
SUBSECTIONS (H3s): {subsections}
WAYZYY MENTIONS USED SO FAR: {wayzyy_count} (hard limit: 5 total for the whole article)

RESEARCH BRIEF (use this for facts, real data, local insights):
{research_brief}

SECTIONS ALREADY WRITTEN (for context — do NOT repeat any adjective or phrase already used):
{previous_sections}

---

Write ONLY the "{section_heading}" section now.

STRICT RULES — violating these will make the article unpublishable:

KEYWORD REPETITION:
- Never use the full topic name "{primary_keyword}" more than 2 times in this section
- Instead rotate these synonyms: "the temple", "the site", "the complex", "this 12th-century structure", "the Kadamba shrine"
- Read the previous sections above — do NOT repeat any phrase or sentence structure already used

ADJECTIVES — these are BANNED (already overused across travel writing):
stunning, breathtaking, beautiful, serene, peaceful, vibrant, picturesque, magnificent,
gorgeous, lovely, amazing, incredible, wonderful, fantastic, perfect, paradise, ultimate,
must-visit, hidden gem, hidden gems, picture-perfect, nestled, charming, quaint

INSTEAD use specific observations:
- NOT "the stunning view" → YES "you can see the river valley from the top step"
- NOT "a serene atmosphere" → YES "on weekday mornings, the only sounds are birds and the occasional temple bell"
- NOT "peaceful surroundings" → YES "the forest here is thick enough to block out road noise"

AI PHRASES — completely banned:
moreover, furthermore, additionally, in conclusion, to summarize, it is important to note,
it is worth mentioning, needless to say, delve into, embark on, tapestry, at the end of the day

WAYZYY MENTIONS:
- Only add a Wayzyy mention if {wayzyy_count} is less than 4 AND this section is directly about accommodation or booking
- If you add one, use EXACTLY ONE of these — do not paraphrase or repeat the same template twice in the article:
  * "Platforms like Wayzyy make it easier to find verified villas near [specific area]."
  * "Wayzyy lets you filter stays by [specific amenity] — handy if you're planning [specific trip type]."
  * "At Wayzyy, we've noticed guests increasingly ask about [specific thing] when booking near [area]."
- If this section is NOT about accommodation/booking, write zero Wayzyy mentions

SENTENCE VARIETY:
- Mix lengths: some 1 sentence paragraphs, some 3-4 sentences
- Do not start consecutive sentences with the same word
- Active voice: "Visitors can rent scooters" not "Scooters can be rented"

FORMAT:
- Start with: ## {section_heading}
- H3s: ### [title]
- Max 320 words total for this section
- End naturally — no "In conclusion" or "To summarize"

Write the section now:
"""

INTRO_WRITER_PROMPT = """
You are writing the introduction for a Goa travel article for Wayzyy.

ARTICLE TITLE: {title}
PRIMARY KEYWORD: {primary_keyword}
INTRO APPROACH: {intro_approach}

RESEARCH BRIEF:
{research_brief}

---

Write a compelling 2-3 paragraph introduction. 150-250 words total.

BANNED OPENERS — starting with any of these will disqualify the intro:
- "Nestled", "Tucked away", "Hidden away", "Situated"
- "Welcome to", "Are you planning", "Have you ever"
- "Goa is one of India's most popular"
- "If you're looking for the perfect"
- Any sentence that starts with the topic name

BANNED ADJECTIVES (do not use even once):
stunning, breathtaking, magnificent, gorgeous, vibrant, picture-perfect, hidden gem

BANNED AI PHRASES:
moreover, furthermore, additionally, in conclusion, delve into, embark on, tapestry

STRONG INTRO PATTERNS — pick one:
1. Open with what people search for → then honestly set expectations:
   "Most Goa guides describe {primary_keyword} as [X]. They're not wrong, but there's more to it."
2. Direct observation that surprises:
   "The roads to {primary_keyword} are narrow. The parking is basic. The facilities are minimal. None of that matters once you're standing in front of it."
3. The contrast opener:
   "Goa has beaches, clubs, and Instagram-friendly cafés. {primary_keyword} is none of those things — and that's exactly the point."

RULES:
- No H1 — title is handled separately
- Paragraph 1: hook — honest angle on what this place actually is
- Paragraph 2: what this guide covers (specific, practical)
- Paragraph 3 (optional): who this is for / who it's NOT for
- Active voice throughout
- Grade 7-9 readability — short words, clear sentences

Write the intro now:
"""

FAQ_WRITER_PROMPT = """
You are writing the FAQ section for a Goa travel article for Wayzyy.

ARTICLE TITLE: {title}
TOPIC: {topic}

FAQ QUESTIONS FROM RESEARCH:
{faq_questions}

RESEARCH BRIEF (for accurate answers):
{research_brief}

---

Write a complete FAQ section.

FORMAT:
## Frequently Asked Questions About {topic}

**[Question]**
[2-4 sentence answer, direct and practical]

RULES:
- Answer every question in the list
- Answers must be practical and specific — real costs, real timings, real advice
- No hedging ("it depends", "generally speaking") — be direct
- If you genuinely don't know a fact, say "check with your host/hotel directly" rather than guessing
- Active voice
- No AI phrases

Write the FAQ section now:
"""

FINAL_THOUGHTS_PROMPT = """
You are writing the final section of a {niche} article for {brand_name}.

ARTICLE TITLE: {{title}}
TOPIC: {{topic}}

RESEARCH BRIEF:
{{research_brief}}

ARTICLE SUMMARY (what was covered):
{{article_summary}}

---

Write a "Final Thoughts" section.

RULES:
- H2: ## Final Thoughts: Is {{topic}} Worth It?  (adapt to topic)
- 150-200 words
- End with a clear recommendation — who should go, who shouldn't
- Do NOT start with "In conclusion" or "To summarize"
- End with a confident opinion, not a hedge
- After Final Thoughts, add the {brand_name} CTA:

---
*Looking for a {offering} in {location_keyword}? {brand_name} helps you discover verified stays —
{offering_plural} — with transparent pricing and direct host access.
[Browse {location_keyword} villas on {brand_name} →]({blog_url})*

*Want to list your property on {brand_name}? Email us at {contact_email} — {brand_name} is launching soon in {location_keyword}.*

Write the Final Thoughts section now:
""".format(
    niche=_brand["niche"],
    brand_name=_brand["name"],
    location_keyword=_brand["location_keyword"],
    blog_url=_brand["blog_url"],
    contact_email=_brand["contact_email"],
    offering=_brand["offering"],
    offering_plural=_brand["offering_plural"],
)


WRITER_MODEL = "kimi-k2.7-code-highspeed"
FALLBACK_MODEL = "llama-3.3-70b-versatile"


def get_deepseek_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["KIMI_API_KEY"],
        base_url="https://api.moonshot.ai/v1",
    )


def get_fallback_client() -> OpenAI:
    """Groq — used automatically if Kimi's daily quota runs out mid-article."""
    return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )


def parse_outline(outline: str) -> dict:
    """Parse the outline text into structured sections."""
    lines = outline.strip().split("\n")

    parsed = {
        "title": "",
        "meta_description": "",
        "primary_keyword": "",
        "intro_approach": "",
        "sections": [],
        "faq_questions": [],
        "wayzyy_spots": [],
    }

    current_h2 = None
    in_faq = False
    in_intro = False
    in_outline = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("TITLE:"):
            parsed["title"] = line.replace("TITLE:", "").strip()
        elif line.startswith("META DESCRIPTION:"):
            parsed["meta_description"] = line.replace("META DESCRIPTION:", "").strip()
        elif line.startswith("PRIMARY KEYWORD:"):
            parsed["primary_keyword"] = line.replace("PRIMARY KEYWORD:", "").strip()
        elif line.startswith("WAYZYY MENTION SPOTS:"):
            parsed["wayzyy_spots"] = line.replace("WAYZYY MENTION SPOTS:", "").strip()
        elif line.startswith("INTRO APPROACH:"):
            in_intro = True
            in_outline = False
            in_faq = False
        elif line.startswith("OUTLINE:"):
            in_outline = True
            in_intro = False
            in_faq = False
        elif line.startswith("FAQ QUESTIONS"):
            in_faq = True
            in_outline = False
            in_intro = False
        elif in_intro and not line.startswith(("H2:", "H3:", "FAQ", "OUTLINE", "INTERNAL", "CONTENT")):
            parsed["intro_approach"] += " " + line
        elif in_outline:
            if line.startswith("H2:"):
                h2_title = line.replace("H2:", "").strip()
                current_h2 = {"heading": h2_title, "h3s": []}
                parsed["sections"].append(current_h2)
            elif line.startswith("H3:") and current_h2:
                h3_title = line.replace("H3:", "").strip()
                current_h2["h3s"].append(h3_title)
        elif in_faq:
            if re.match(r"^\d+\.", line):
                question = re.sub(r"^\d+\.\s*", "", line).strip()
                if question:
                    parsed["faq_questions"].append(question)

    return parsed


def write_section(
    client: OpenAI,
    title: str,
    primary_keyword: str,
    section: dict,
    research_brief: str,
    previous_sections: str,
    wayzyy_count: int = 0,
) -> str:
    """Write a single H2 section."""

    h3_list = "\n".join([f"- {h3}" for h3 in section["h3s"]]) if section["h3s"] else "No specific H3s — use judgment"

    prompt = SECTION_WRITER_PROMPT.format(
        title=title,
        primary_keyword=primary_keyword,
        section_heading=section["heading"],
        subsections=h3_list,
        wayzyy_count=wayzyy_count,
        research_brief=research_brief[:3000],
        previous_sections=previous_sections[-2000:] if previous_sections else "None yet — this is the first section.",
    )

    def _kimi_call(p=prompt):
        return client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": p}],
            temperature=1, max_tokens=2000,
        )

    def _groq_call(p=prompt):
        return get_fallback_client().chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": p}],
            temperature=0.7, max_tokens=800,
        )

    response = call_with_fallback(_kimi_call, _groq_call)
    section_text = response.choices[0].message.content.strip()

    # Self-healing check — rewrite once if violations found
    violations = check_section(section_text, primary_keyword, wayzyy_count)
    if violations:
        violation_keys = list(violations.keys())
        print(f"  ⚠ Violations found: {violation_keys} — auto-fixing...", file=sys.stderr)
        fix_prompt = build_fix_prompt(section_text, violations, section["heading"], primary_keyword)
        fixed = call_with_fallback(lambda: _kimi_call(fix_prompt), lambda: _groq_call(fix_prompt))
        section_text = fixed.choices[0].message.content.strip()
        print(f"  ✓ Fixed", file=sys.stderr)

    return section_text


def write_intro(client: OpenAI, title: str, primary_keyword: str, intro_approach: str, research_brief: str) -> str:
    """Write the article intro."""
    prompt = INTRO_WRITER_PROMPT.format(
        title=title,
        primary_keyword=primary_keyword,
        intro_approach=intro_approach,
        research_brief=research_brief[:3000],
    )

    response = call_with_fallback(
        lambda: client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=1, max_tokens=1200,
        ),
        lambda: get_fallback_client().chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=500,
        ),
    )

    return response.choices[0].message.content.strip()


def write_faq(client: OpenAI, title: str, topic: str, faq_questions: list, research_brief: str) -> str:
    """Write the FAQ section."""
    questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(faq_questions)])

    prompt = FAQ_WRITER_PROMPT.format(
        title=title,
        topic=topic,
        faq_questions=questions_str,
        research_brief=research_brief[:3000],
    )

    response = call_with_fallback(
        lambda: client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=1, max_tokens=2000,
        ),
        lambda: get_fallback_client().chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=900,
        ),
    )

    return response.choices[0].message.content.strip()


def write_final_thoughts(client: OpenAI, title: str, topic: str, research_brief: str, article_summary: str) -> str:
    """Write the final thoughts + CTA section."""
    prompt = FINAL_THOUGHTS_PROMPT.format(
        title=title,
        topic=topic,
        research_brief=research_brief[:2000],
        article_summary=article_summary[-1500:],
    )

    response = call_with_fallback(
        lambda: client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=1, max_tokens=1000,
        ),
        lambda: get_fallback_client().chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "system", "content": STYLE_GUIDE_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=400,
        ),
    )

    return response.choices[0].message.content.strip()


def write_full_article(parsed_outline: dict, research_brief: str) -> str:
    """
    Write the complete article section by section.
    Returns the full assembled article text.
    """
    client = get_deepseek_client()

    title = parsed_outline["title"]
    primary_keyword = parsed_outline["primary_keyword"]
    topic = primary_keyword or title
    intro_approach = parsed_outline.get("intro_approach", "")
    sections = parsed_outline["sections"]
    faq_questions = parsed_outline["faq_questions"]

    all_parts = []
    total = len(sections)
    wayzyy_count = 0  # track mentions across all sections

    # Write H1
    all_parts.append(f"# {title}\n")

    # Hero image (optional — skipped silently if Pexels has nothing relevant
    # or the key isn't set, never blocks the article from being written)
    from agent.images import get_hero_image, image_markdown
    hero = get_hero_image(f"{topic} Goa")
    if hero:
        all_parts.append(image_markdown(hero) + "\n")
        print(f"  ✓ Hero image found ({hero['photographer']})", file=sys.stderr)

    # Write intro
    print(f"\n[writer] Writing intro...", file=sys.stderr)
    intro = write_intro(client, title, primary_keyword, intro_approach, research_brief)
    all_parts.append(intro + "\n")
    print(f"  ✓ Intro done", file=sys.stderr)

    # Write each H2 section
    for i, section in enumerate(sections):
        heading = section["heading"]

        # Skip FAQ section — we write it separately
        if "frequently asked" in heading.lower() or "faq" in heading.lower():
            continue
        # Skip final thoughts — we write it separately
        if "final thoughts" in heading.lower():
            continue

        print(f"[writer] Writing section {i+1}/{total}: {heading}...", file=sys.stderr)
        previous = "\n\n".join(all_parts[-3:])
        section_text = write_section(
            client, title, primary_keyword, section, research_brief, previous,
            wayzyy_count=wayzyy_count,
        )
        # Update wayzyy counter from what was actually written
        wayzyy_count += section_text.lower().count("wayzyy")
        all_parts.append(section_text + "\n")
        print(f"  ✓ Done (Wayzyy mentions so far: {wayzyy_count})", file=sys.stderr)

    # Write FAQ
    if faq_questions:
        print(f"[writer] Writing FAQ ({len(faq_questions)} questions)...", file=sys.stderr)
        faq_text = write_faq(client, title, topic, faq_questions, research_brief)
        all_parts.append(faq_text + "\n")
        print(f"  ✓ FAQ done", file=sys.stderr)

    # Write Final Thoughts + CTA
    print(f"[writer] Writing final thoughts...", file=sys.stderr)
    article_so_far = "\n\n".join(all_parts)
    final = write_final_thoughts(client, title, topic, research_brief, article_so_far)
    all_parts.append(final + "\n")
    print(f"  ✓ Final thoughts done", file=sys.stderr)

    full_article = "\n\n".join(all_parts)
    print(f"\n[writer] Article complete. ~{len(full_article.split())} words.", file=sys.stderr)
    return full_article
