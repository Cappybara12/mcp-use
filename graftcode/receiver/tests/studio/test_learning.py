import pytest

from article_receiver.studio import docs, rulebook, seo, sources
from article_receiver.studio.store import StudioError

HTML = """<html><head><title>T</title><meta name="description" content="d"></head><body><nav>menu</nav><article>
<h1>5 Ways to Grow (2026)</h1><p>Have you ever wondered about growth? It matters to teams today and tomorrow.</p>
<h2>Why it matters</h2><p>Because <strong>it</strong> works for many people in many situations all the time, so start now.</p>
<h2>FAQ</h2><h3>What is growth?</h3><p>Growth is more users.</p><h3>How long?</h3><p>Weeks.</p>
<a href="https://other.com/x">src</a><a href="/about">about</a></article><footer>f</footer></body></html>"""


def test_html_is_parsed_into_structure():
    d = docs.parse_html(HTML, "https://acme.com/blog/x")
    assert d["title"] == "5 Ways to Grow (2026)" and d["description"] == "d"
    assert d["faq_pairs"] == [("What is growth?", "Growth is more users."), ("How long?", "Weeks.")]
    assert d["has_faq_heading"] and (d["internal_links"], d["external_links"]) == (1, 1) and d["bold"] == 1
    assert "menu" not in d["text"]


def test_jsonld_faq_schema_is_detected():
    page = ('<html><body><article><h1>T</h1><p>' + "word " * 30 + '</p></article>'
            '<script type="application/ld+json">{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Q1?",'
            '"acceptedAnswer":{"@type":"Answer","text":"A1"}}]}</script></body></html>')
    d = docs.parse_html(page)
    assert d["has_faq_schema"] and d["faq_pairs"] == [("Q1?", "A1")] and "FAQPage" in d["jsonld_types"]


def test_markdown_is_parsed_including_front_matter_and_links():
    md = ("---\ntitle: \"From front matter\"\n---\n# Real Title\n\nIntro? Yes it is long enough to count as a real paragraph here.\n\n"
          "## FAQ\n### What is it?\nA thing.\n\nSee [x](https://a.com) and https://b.com/z and https://me.com/own .\n")
    d = docs.parse_markdown(md, "https://me.com/p")
    assert d["title"] == "Real Title" and d["faq_pairs"] == [("What is it?", "A thing.")]
    assert (d["external_links"], d["internal_links"]) == (2, 1)


def test_code_blocks_are_ignored():
    d = docs.parse_markdown("# T\n\n```\n# not a heading\n```\n\nReal paragraph with enough words in it to be counted properly.\n")
    assert [h for h in d["headings"] if h[1] == "not a heading"] == []


# ── measuring and learning ────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("Have you tried this? It works.", "question"), ("If you run a team, read on.", "direct"),
    ("Last spring we changed our process.", "story"), ("Nine of 10 teams quit in 2025.", "statistic"), ("Funnels are maps.", "claim")])
def test_opener_classification(text, expected):
    assert rulebook.opener_type(text) == expected


def test_reading_ease_and_hooks():
    assert rulebook.flesch("The cat sat. The dog ran.") > 80
    assert rulebook.flesch("Notwithstanding considerable organisational heterogeneity, implementation necessitates comprehensive deliberation.") < 20
    assert rulebook.has_hook("Most teams get this wrong.") and not rulebook.has_hook("This is a description of a thing in the world.")


def _sample_posts():
    out = []
    for url in sources.list_sample_posts():
        doc = sources.to_analysed(sources.fetch_document(url, "sample"))
        out.append((rulebook.analyze_post(doc, url), doc["text"]))
    return [p for p, _ in out], [t for _, t in out]


def test_learning_from_the_sample_blog_finds_its_habits():
    posts, texts = _sample_posts()
    learned = rulebook.learn(posts, texts)
    kinds = {r["kind"]: r for r in learned["rules"]}
    assert learned["stats"]["posts"] == 5 and learned["stats"]["mean_em_dash_per_1000"] == 0
    assert "Do not use em dashes" in kinds["em_dash"]["text"] and kinds["em_dash"]["params"]["max_per_1000"] == 0.5
    assert kinds["opener"]["params"]["allowed"] == ["question"] and "100%" in kinds["opener"]["evidence"]
    assert kinds["faq"]["params"]["min_pairs"] >= 2 and "FAQPage" in kinds["faq"]["text"]
    assert all(r["evidence"] and r["enabled"] and r["source"] == "learned" for r in learned["rules"])


def test_em_dash_blogs_get_a_different_rule():
    doc = docs.parse_markdown("# T\n\n" + " ".join(["Plain words — and a dash, again and again, so the paragraph gets long enough."] * 12))
    learned = rulebook.learn([rulebook.analyze_post(doc)] * 4)
    rule = next(r for r in learned["rules"] if r["kind"] == "em_dash")
    assert "part of this voice" in rule["text"] and rule["params"]["max_per_1000"] > 0.5


def test_relearning_keeps_the_persons_choices():
    posts, texts = _sample_posts()
    first = rulebook.merge_rulebook({}, rulebook.learn(posts, texts), [])
    first["rules"][0]["enabled"] = False
    first["rules"][1].update(text="My own wording", edited=True)
    first["rules"].append(rulebook.new_custom_rule("Never say synergy", "banned_phrases", {"phrases": ["synergy"]}))
    second = rulebook.merge_rulebook(first, rulebook.learn(posts, texts), [])
    ids = {r["id"]: r for r in second["rules"]}
    assert ids[first["rules"][0]["id"]]["enabled"] is False
    assert ids[first["rules"][1]["id"]]["text"] == "My own wording"
    assert any(r["source"] == "custom" for r in second["rules"])


def test_rules_prompt_lists_only_enabled_rules():
    rb = {"rules": [{"text": "A", "enabled": True}, {"text": "B", "enabled": False}]}
    assert "- A" in rulebook.rules_prompt(rb) and "- B" not in rulebook.rules_prompt(rb)
    assert rulebook.rules_prompt({"rules": []}) == ""


# ── checking drafts ───────────────────────────────────────────────────────────

GOOD = ("---\ntitle: \"Retention Tables: A Quick Guide\"\ndescription: \"How to read a retention table in five minutes, with a worked example you can copy.\"\n---\n"
        "# Retention Tables: A Quick Guide\n\nHave you ever stared at a retention table and learned nothing? A retention table shows who comes back. " + "Read across a row. " * 40 +
        "\n\n## Why a retention table matters\n" + "It tells you who stays. " * 20 + "\n\n## How to read it\n" + "Look for the flat part. " * 20 +
        "\n\n## Mistakes\nSee [Amplitude](https://amplitude.com/blog) for more. " + "Do not guess. " * 20 +
        "\n\n## FAQ\n### What is a cohort?\nA group of users.\n\n### Why flat?\nBecause they stayed.\n\n### How often?\nWeekly.\n")


def test_good_draft_passes_core_seo_checks():
    r = seo.check(GOOD, "retention table", {"rules": []})
    failing = {c["id"] for c in r["checks"] if not c["ok"]}
    assert not failing & {"h1", "kw_title", "kw_intro", "kw_h2", "faq", "meta", "ext_links"}
    assert r["slug"] == "retention-tables-a-quick-guide" and len(r["faq_schema"]["mainEntity"]) == 3
    assert r["faq_script"].startswith('<script type="application/ld+json">')


def test_missing_keyword_and_stuffing_are_flagged():
    bare = "# A title\n\nNothing relevant here at all, just words repeating " + "filler " * 80 + "\n\n## One\nx\n"
    assert any(c["id"] == "kw_title" and not c["ok"] for c in seo.check(bare, "retention table", {"rules": []})["checks"])
    stuffed = "# Retention table\n\n" + "retention table " * 100
    assert any(c["id"] == "kw_density" and not c["ok"] and c["severity"] == "error"
               for c in seo.check(stuffed, "retention table", {"rules": []})["checks"])


def test_no_keyword_is_reported_not_crashed():
    assert any(c["id"] == "kw_missing" for c in seo.check("# T\n\nBody text here.", "", {"rules": []})["checks"])


def test_rulebook_rules_are_checked_against_the_draft():
    rb = {"rules": [
        {"id": "em", "kind": "em_dash", "text": "No em dashes", "params": {"max_per_1000": 0.5}, "enabled": True},
        {"id": "len", "kind": "length", "text": "Be short", "params": {"min": 10, "max": 50, "target": 30}, "enabled": True},
        {"id": "ban", "kind": "banned_phrases", "text": "No synergy", "params": {"phrases": ["synergy"]}, "enabled": True},
        {"id": "off", "kind": "banned_phrases", "text": "Disabled", "params": {"phrases": ["the"]}, "enabled": False}]}
    text = "# T\n\nOur synergy — is great. " + "words " * 80
    results = {r["rule_id"]: r["ok"] for r in rulebook.check_rules(docs.parse_markdown(text), rb)}
    assert results == {"em": False, "len": False, "ban": False}          # the disabled rule is not checked


def test_a_length_rule_replaces_the_generic_word_count_check():
    rb = {"rules": [{"id": "len", "kind": "length", "text": "x", "params": {"min": 1, "max": 9999, "target": 5}, "enabled": True}]}
    assert "words" not in {c["id"] for c in seo.check("# T\n\nshort", "", rb)["checks"]}
    assert "words" in {c["id"] for c in seo.check("# T\n\nshort", "", {"rules": []})["checks"]}


def test_keyword_opportunity_ranking():
    assert seo.opportunity({"volume": 5000, "difficulty": 20}) > seo.opportunity({"volume": 5000, "difficulty": 80})
    assert seo.opportunity({"volume": 5000, "difficulty": 40, "intent": "informational"}) > seo.opportunity({"volume": 5000, "difficulty": 40})
    assert seo.opportunity({"volume": None, "difficulty": None}) == 0


# ── sources ───────────────────────────────────────────────────────────────────

def test_feed_parsing_rss_and_atom():
    rss = b'<rss><channel><item><title>One</title><link>https://a/1</link><description>&lt;b&gt;Hi&lt;/b&gt;</description></item></channel></rss>'
    atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Two</title><link href="https://a/2"/><summary>S</summary></entry></feed>'
    assert sources.parse_feed(rss)[0] == {"title": "One", "link": "https://a/1", "summary": "Hi", "published": ""}
    assert sources.parse_feed(atom)[0]["link"] == "https://a/2"


def test_xml_bombs_are_rejected():
    bomb = (b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
            b'<rss><channel><item><title>&lol2;</title></item></channel></rss>')
    with pytest.raises(StudioError, match="entity"):
        sources.parse_feed(bomb)
    with pytest.raises(StudioError):
        sources.parse_feed(b"<rss>" + b"x" * 3_000_000)


def test_sample_references_are_strict():
    for bad in ("sample:feed/../x", "sample:post/A", "sample:other/x", "sample:feed/missing"):
        with pytest.raises(StudioError):
            sources.read_sample(bad)
    assert len(sources.read_feed("sample:feed/acme")) == 5


def test_discovery_finds_posts_through_a_feed_or_sitemap(mock):
    mock.on("GET", "/blog", b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head></html>')
    mock.on("GET", "/feed.xml", b'<rss><channel><item><title>A</title><link>https://x/a</link></item>'
                                b'<item><title>B</title><link>https://x/b</link></item></channel></rss>')
    assert sources.discover_posts(mock.url + "/blog", 5) == ["https://x/a", "https://x/b"]
    mock.routes.clear()
    mock.on("GET", "/sitemap.xml", f"<urlset><url><loc>{mock.url}/blog/one</loc></url><url><loc>{mock.url}/about</loc></url></urlset>".encode())
    assert sources.discover_posts(mock.url, 5) == [f"{mock.url}/blog/one"]
    mock.routes.clear()
    with pytest.raises(StudioError, match="Could not find"):
        sources.discover_posts(mock.url, 5)


def test_long_tail_keywords_are_not_penalised_for_their_length():
    keyword = "how to read a retention table"
    text = "# " + keyword.title() + "\n\n" + ("Plain filler words fill the page here. " * 60) + keyword + " matters. " + keyword + " again.\n"
    density = next(c for c in seo.check(text, keyword, {"rules": []})["checks"] if c["id"] == "kw_density")
    assert density["ok"], density            # 2 uses in about 400 words is natural, whatever the phrase length


# ── tables ────────────────────────────────────────────────────────────────────

def test_tables_are_counted_in_html_and_markdown():
    html = "<html><body><article><h1>T</h1><p>" + "word " * 30 + "</p><table><tr><td>a</td></tr></table><table><tr><td>b</td></tr></table></article></body></html>"
    assert docs.parse_html(html)["tables"] == 2
    md = "# T\n\nIntro words here and there for the paragraph to count.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nText.\n\n| C | D |\n| :-- | --: |\n| 3 | 4 |\n"
    assert docs.parse_markdown(md)["tables"] == 2
    assert docs.parse_markdown("# T\n\n```\n| A | B |\n|---|---|\n```\n\nPlain words only.\n")["tables"] == 0
    assert docs.parse_markdown("# T\n\nA line with a | pipe but no table.\n")["tables"] == 0


def _post(tables):
    md = "# Post\n\nHave you wondered about this? " + "Plain words fill this post. " * 20 + ("\n\n| A | B |\n|---|---|\n| 1 | 2 |\n" * tables) + "\n"
    return rulebook.analyze_post(docs.parse_markdown(md))


def test_a_blog_that_uses_comparison_tables_gets_a_tables_rule():
    learned = rulebook.learn([_post(1), _post(1), _post(0), _post(1)])
    rule = next(r for r in learned["rules"] if r["id"] == "tables")
    assert "comparison table" in rule["text"] and "3 of 4 posts (75%)" in rule["evidence"]
    assert rule["kind"] == "note"                      # guidance for the writer, never a failing check


def test_a_blog_without_tables_gets_no_tables_rule():
    assert not any(r["id"] == "tables" for r in rulebook.learn([_post(0), _post(0), _post(0), _post(1), _post(0)])["rules"])
