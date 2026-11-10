import json

import pytest


def test_status_reports_demo_mode(service):
    status = json.loads(service.get_pipeline_status())
    assert status["status"].startswith("online")
    assert "demo" in status["status"]
    assert status["queue_stats"]["pending_topics_count"] == 3
    assert status["queue_stats"]["completed_drafts_count"] == 1


def test_list_pending_topics_reads_front_matter(service):
    topics = json.loads(service.list_pending_topics())
    titles = {t["title"] for t in topics}
    assert "Villas with private pools in Vagator" in titles
    villa = next(t for t in topics if "Vagator" in t["title"])
    assert villa["sources_count"] == 4


def test_list_pending_topics_caps_at_twelve(service):
    assert len(json.loads(service.list_pending_topics())) <= 12


def test_topic_sources_parse_platform_title_url(service):
    sources = json.loads(service.get_topic_sources("Vagator"))
    assert sources and {"platform", "title", "url"} <= sources[0].keys()


def test_suggest_picks_a_business_relevant_topic(service):
    suggestion = json.loads(service.suggest_next_article())
    assert "Vagator" in suggestion["topic"]
    assert suggestion["sources_count"] == 4


def test_write_article_demo_creates_labelled_draft(service):
    result = json.loads(service.write_article("Quiet beaches in Benaulim"))
    assert result["status"] == "completed (demo)"
    draft = json.loads(service.get_draft(result["filename"]))
    assert "Demo-mode placeholder" in draft["content"]


def test_write_article_rejects_empty_topic(service):
    with pytest.raises(ValueError):
        service.write_article("   ")


def test_style_check_flags_cliches(service):
    service.save_draft("cliche.md", "# Title\n\nGoa is a hidden gem. Moreover, it is vibrant.\n\n## Section\nText.")
    audit = json.loads(service.run_style_check("cliche.md"))
    assert {"hidden gem", "moreover", "vibrant"} <= set(audit["ai_cliches_found"])
    assert audit["brand_score"] < 100


def test_style_check_short_sample_draft_explains_its_score(service):
    audit = json.loads(service.run_style_check("sample-assagao"))
    # The bundled sample is short on purpose: the audit must say why it loses points.
    assert audit["brand_score"] < 100
    assert any("900 words" in r for r in audit["recommendations"])
    assert "Includes Pexels attribution" in audit["passed_checks"]


def test_missing_draft_raises(service):
    with pytest.raises(ValueError):
        service.get_draft("does-not-exist")


def test_save_draft_rejects_path_like_names(service, tmp_path):
    with pytest.raises(ValueError):
        service.save_draft("../../escape.md", "x")
    assert not (tmp_path / "escape.md").exists()


def test_push_requires_real_pipeline(service):
    with pytest.raises(RuntimeError):
        service.push_to_github("anything.md")


def test_scanner_skipped_in_demo_mode(service):
    result = json.loads(service.run_scanner())
    assert result["status"].startswith("skipped")


def test_suggest_skips_topics_that_already_have_a_draft(service):
    first = json.loads(service.suggest_next_article())["topic"]
    service.write_article(first)
    second = json.loads(service.suggest_next_article())["topic"]
    assert second != first


def test_suggest_raises_when_every_topic_is_drafted(service):
    for t in json.loads(service.list_pending_topics()):
        service.write_article(t["title"])
    with pytest.raises(ValueError):
        service.suggest_next_article()


def test_snippet_is_readable_not_raw_front_matter(service):
    for topic in json.loads(service.list_pending_topics()):
        assert not topic["snippet"].startswith("---")
        assert "date:" not in topic["snippet"]


def test_source_with_empty_url_is_still_listed(service, tmp_path):
    review = next(p for p in __import__("pathlib").Path(__import__("os").environ["WAYZYY_REVIEW_DIR"]).glob("*.md"))
    review.write_text(
        "---\nkeyword: Empty url topic\nplatforms: research\nclassification: new_pillar\n---\n\n"
        "## Trend Sources\n- [research] [Mentioned while researching X]()\n",
        encoding="utf-8",
    )
    sources = json.loads(service.get_topic_sources("Empty url topic"))
    assert sources == [{"platform": "research", "title": "Mentioned while researching X", "url": ""}]


def test_find_similar_articles_falls_back_to_keywords(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    results = json.loads(service.find_similar_articles("cafe guide in Assagao"))
    assert results[0]["filename"].endswith("assagao-cafe-guide.md")
    assert results[0]["engine"] == "keyword-overlap"


def test_find_similar_articles_survives_unreachable_sie(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://127.0.0.1:9")
    results = json.loads(service.find_similar_articles("assagao cafe"))
    assert results and results[0]["engine"] == "keyword-overlap"


def test_find_similar_articles_rejects_empty_query(service):
    with pytest.raises(ValueError):
        service.find_similar_articles("  ")


def test_find_similar_articles_defaults_a_missing_limit(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    assert json.loads(service.find_similar_articles("assagao cafe", None))


def test_compare_search_engines_without_sie(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    out = json.loads(service.compare_search_engines("assagao cafe", 2))
    assert out["keyword"]["results"][0]["filename"].endswith("assagao-cafe-guide.md")
    assert len(out["keyword"]["results"]) <= 2
    assert out["sie"]["available"] is False and "SIE_URL" in out["sie"]["message"]


def test_compare_search_engines_reports_unreachable_sie(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://127.0.0.1:9")
    out = json.loads(service.compare_search_engines("assagao cafe", None))
    assert out["sie"]["available"] is False and "not reachable" in out["sie"]["message"]
    assert out["keyword"]["results"]


def test_compare_search_engines_uses_sie_when_up(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://sie")
    monkeypatch.setattr(
        "article_receiver.service._embed_with_sie",
        lambda texts: [[1.0, 0.0]] + [[float(i == 0), float(i != 0)] for i in range(len(texts) - 1)],
    )
    out = json.loads(service.compare_search_engines("anything", 1))
    assert out["sie"]["available"] is True
    assert out["sie"]["results"][0]["engine"].startswith("sie:")


def test_sie_embeds_each_draft_once(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://sie")
    monkeypatch.setattr("article_receiver.service._EMBED_CACHE", {})
    calls = []

    def fake(texts):
        calls.append(len(texts))
        return [[1.0, float(i)] for i in range(len(texts))]

    monkeypatch.setattr("article_receiver.service._embed_with_sie", fake)
    service.find_similar_articles("first", 2)
    service.find_similar_articles("second", 2)
    assert calls[0] > 1 and calls[1] == 1  # second search embeds only the query


# ── Phase 1: brand relevance and coverage with SIE (embeddings faked by keyword) ──

def _fake_sie(monkeypatch, extra=()):
    """Fake SIE: a text's vector is [on-brand, politics, cafe, villa, *extra words]."""
    def embed(texts):
        out = []
        for t in texts:
            t = t.lower()
            out.append([
                float(any(w in t for w in ("goa", "villa", "beach", "cafe", "travel", "monsoon"))),
                float("bjp" in t),
                float("cafe" in t),
                float("villa" in t),
            ] + [float(w in t) for w in extra])
        return out

    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://sie")
    monkeypatch.setattr("article_receiver.service._EMBED_CACHE", {})
    monkeypatch.setattr("article_receiver.service._embed_with_sie", embed)


def _add_offbrand_topic(sources=50):
    import os, pathlib
    review = pathlib.Path(os.environ["WAYZYY_REVIEW_DIR"])
    links = "\n".join(f"- [news] [Story {i}](https://example.com/{i})" for i in range(sources))
    (review / "2026-01-09_bjp-dispute.md").write_text(
        f"---\nkeyword: BJP dispute\n---\n\n## Trend Sources\n{links}\n", encoding="utf-8")


def test_keyword_suggest_picks_a_popular_offbrand_topic(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    _add_offbrand_topic()
    suggestion = json.loads(service.suggest_next_article())
    assert suggestion["topic"] == "BJP dispute"  # the behaviour SIE fixes
    assert suggestion["engine"] == "keyword" and suggestion["relevance"] is None


def test_sie_suggest_skips_offbrand_and_covered_topics(service, monkeypatch):
    _fake_sie(monkeypatch)
    _add_offbrand_topic()
    suggestion = json.loads(service.suggest_next_article())
    assert "Vagator" in suggestion["topic"]
    assert suggestion["skipped_off_brand"] == 1  # BJP dispute
    assert suggestion["skipped_covered"] == 1  # cafes topic vs the Assagao cafe draft
    assert suggestion["engine"].startswith("keyword + sie:")
    assert suggestion["relevance"] > 0.25 and "Superlinked SIE" in suggestion["rationale"]


def test_sie_suggest_explains_when_nothing_is_left(service, monkeypatch):
    _fake_sie(monkeypatch)
    monkeypatch.setitem(__import__("article_receiver.service", fromlist=["CONFIG"]).CONFIG["semantic"], "min_relevance", 2.0)
    with pytest.raises(ValueError, match="min_relevance"):
        service.suggest_next_article()


def test_unreachable_sie_keeps_keyword_suggestions(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    expected = json.loads(service.suggest_next_article())["topic"]
    monkeypatch.setattr("article_receiver.service.SIE_URL", "http://127.0.0.1:9")
    suggestion = json.loads(service.suggest_next_article())
    assert suggestion["topic"] == expected and suggestion["engine"] == "keyword"


def test_topic_list_shows_relevance_and_coverage(service, monkeypatch):
    _fake_sie(monkeypatch)
    topics = {t["title"].lower(): t for t in json.loads(service.list_pending_topics())}
    cafes = next(t for k, t in topics.items() if "cafe" in k)
    villas = next(t for k, t in topics.items() if "villa" in k)
    assert cafes["covered_by"].endswith("assagao-cafe-guide.md")
    assert villas["covered_by"] == "" and villas["relevance"] > 0.25


def test_topic_list_without_sie_has_no_relevance(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    assert all(t["relevance"] is None for t in json.loads(service.list_pending_topics()))


# ── Phase 2: related reads from published posts ──

POSTS_TS = '''export const blogPosts: BlogPostMeta[] = [
  {
    slug: "working-from-a-cafe-in-assagao",
    title: "Working From a Cafe in Assagao: A Practical Guide",
    description: "Laptop-friendly cafes in Assagao.",
  },
  {
    slug: "best-cafes-north-goa",
    title: "Best Cafes in North Goa",
    description: "Coffee, wifi and quiet cafe mornings in North Goa.",
  },
  {
    slug: "goa-villa-guide",
    title: "Villas in Goa",
    description: "How to pick a villa with a pool.",
  },
  {
    slug: "assembly-politics",
    title: "BJP dispute explained",
    description: "Local BJP politics.",
  },
];
'''

DRAFT = "2026-01-01_sample-assagao-cafe-guide.md"


def _posts_file(tmp_path, monkeypatch, text=POSTS_TS):
    from article_receiver import service as svc_mod
    path = tmp_path / "blogPosts.ts"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setitem(svc_mod.CONFIG["semantic"], "site_posts_file", str(path))
    return path


def _draft_path():
    import os, pathlib
    return pathlib.Path(os.environ["WAYZYY_DRAFTS_DIR"]) / DRAFT


def test_related_links_need_published_posts(service, monkeypatch, tmp_path):
    from article_receiver import service as svc_mod
    monkeypatch.setitem(svc_mod.CONFIG["semantic"], "site_posts_file", str(tmp_path / "missing.ts"))
    out = json.loads(service.suggest_related_links(DRAFT, 3))
    assert out["links"] == [] and "No published posts" in out["message"]


def test_related_links_keyword_fallback(service, monkeypatch, tmp_path):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    _posts_file(tmp_path, monkeypatch)
    out = json.loads(service.suggest_related_links(DRAFT, 3))
    assert out["engine"] == "keyword-overlap" and "Superlinked SIE" in out["message"]
    # The post with the same title is this draft's published copy, never a link.
    assert out["published_as"] == "/blog/working-from-a-cafe-in-assagao"
    assert out["links"][0]["url"] == "/blog/best-cafes-north-goa"
    assert all(l["slug"] != "working-from-a-cafe-in-assagao" for l in out["links"])


def test_related_links_with_sie_skip_weak_matches(service, monkeypatch, tmp_path):
    _fake_sie(monkeypatch, extra=("assagao", "north"))
    _posts_file(tmp_path, monkeypatch)
    out = json.loads(service.suggest_related_links(DRAFT, 3))
    assert out["engine"].startswith("sie:")
    assert out["published_as"] == "/blog/working-from-a-cafe-in-assagao"
    slugs = [l["slug"] for l in out["links"]]
    assert slugs[0] == "best-cafes-north-goa"
    assert "assembly-politics" not in slugs  # below link_min_similarity


def test_related_links_skip_offbrand_drafts(service, monkeypatch, tmp_path):
    _fake_sie(monkeypatch, extra=("assagao", "north"))
    _posts_file(tmp_path, monkeypatch)
    _draft_path().write_text("# BJP dispute in Sanguem\n\nBJP leaders disagree.\n", encoding="utf-8")
    out = json.loads(service.suggest_related_links(DRAFT, 3))
    assert out["links"] == [] and "off-brand" in out["message"]


def test_related_links_flag_near_duplicate_posts(service, monkeypatch, tmp_path):
    _fake_sie(monkeypatch, extra=("assagao", "north"))
    extra_post = '  {\n    slug: "assagao-cafe-notes",\n    title: "Assagao Cafe Notes",\n    description: "More cafes.",\n  },\n];'
    _posts_file(tmp_path, monkeypatch, POSTS_TS.replace("];", extra_post))
    out = json.loads(service.suggest_related_links(DRAFT, 3))
    assert out["published_as"] == "/blog/working-from-a-cafe-in-assagao"
    dup_refs = [d["ref"] for d in out["near_duplicates"]]
    assert dup_refs == ["/blog/assagao-cafe-notes"]  # a second live post on the same topic
    assert all(l["url"] not in dup_refs for l in out["links"])


def test_insert_related_links_writes_and_replaces_section(service, monkeypatch, tmp_path):
    _posts_file(tmp_path, monkeypatch)
    service.insert_related_links(DRAFT, "best-cafes-north-goa, goa-villa-guide")
    text = _draft_path().read_text(encoding="utf-8")
    assert "## Related reads\n\n[Best Cafes in North Goa](/blog/best-cafes-north-goa)\n\n[Villas in Goa](/blog/goa-villa-guide)\n" in text
    service.insert_related_links(DRAFT, "goa-villa-guide")
    text = _draft_path().read_text(encoding="utf-8")
    assert text.count("## Related reads") == 1 and "best-cafes-north-goa" not in text
    assert "Photo credit: Pexels." in text  # the body is kept
    service.insert_related_links(DRAFT, "")
    assert "## Related reads" not in _draft_path().read_text(encoding="utf-8")


def test_insert_related_links_marks_included(service, monkeypatch, tmp_path):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    _posts_file(tmp_path, monkeypatch)
    service.insert_related_links(DRAFT, "best-cafes-north-goa")
    links = {l["slug"]: l for l in json.loads(service.suggest_related_links(DRAFT, 3))["links"]}
    assert links["best-cafes-north-goa"]["included"] is True


def test_insert_related_links_rejects_bad_input(service, monkeypatch, tmp_path):
    _posts_file(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="No published post"):
        service.insert_related_links(DRAFT, "not-a-post")
    with pytest.raises(ValueError, match="exact file name"):
        service.insert_related_links("assagao", "goa-villa-guide")


def test_split_related_keeps_later_sections():
    from article_receiver.service import _split_related
    body, section = _split_related("# T\n\nIntro\n\n## Related reads\n\n[a](/blog/a)\n\n## FAQ\n\nQ\n")
    assert section.startswith("## Related reads") and "[a](/blog/a)" in section
    assert "## FAQ" in body and "[a]" not in body


def test_publisher_slug_matches_site_rule():
    from article_receiver.service import _is_published_copy
    assert _is_published_copy("Tambdi Surla Temple Goa (2026): The Honest Guide", "tambdi-surla-temple-goa-guide")
    assert not _is_published_copy("Goa (2026): Spiritual Tourism", "goa-nightlife-guide")  # "goa" is too generic


def test_rewriting_a_topic_keeps_the_edited_draft(service):
    first = json.loads(service.write_article("Quiet beaches"))
    service.save_draft(first["filename"], "MY HAND EDITS")
    second = json.loads(service.write_article("Quiet beaches"))
    assert second["filename"] != first["filename"]
    assert json.loads(service.get_draft(first["filename"]))["content"] == "MY HAND EDITS"


def test_non_latin_topics_get_distinct_filenames(service):
    a = json.loads(service.write_article("गोवा समुद्र तट"))["filename"]
    b = json.loads(service.write_article("गोवा भोजन"))["filename"]
    assert a != b
    assert not a.endswith("_.md") and not b.endswith("_.md")


def test_banned_opener_found_after_front_matter(service):
    service.save_draft("fm.md", "---\ntitle: X\n---\nLooking for the best beach in Goa?\n## A\n")
    audit = json.loads(service.run_style_check("fm.md"))
    assert "No banned generic opener" not in audit["passed_checks"]


def test_ambiguous_partial_draft_name_is_rejected(service):
    service.save_draft("2026-02-01_beach-one.md", "# One\n")
    service.save_draft("2026-02-02_beach-two.md", "# Two\n")
    with pytest.raises(ValueError, match="ambiguous"):
        service.get_draft("beach")
    assert json.loads(service.get_draft("beach-two"))["filename"] == "2026-02-02_beach-two.md"


def test_empty_topic_sources_is_rejected(service):
    with pytest.raises(ValueError):
        service.get_topic_sources("  ")


def test_fallback_topic_title_drops_any_date_prefix(service, tmp_path):
    from article_receiver import service as mod
    (mod.REVIEW_DIR / "2027-01-05_quiet-beaches.md").write_text("- [x] [y](z)\n")
    titles = [t["title"] for t in json.loads(service.list_pending_topics())]
    assert "Quiet Beaches" in titles


def test_embeddings_survive_a_restart_with_a_disk_cache(service, monkeypatch, tmp_path):
    from article_receiver import service as svc_mod
    cache = tmp_path / "cache" / "sie.json"
    calls = []

    def fake(texts):
        calls.append(len(texts))
        return [[1.0, float(i)] for i in range(len(texts))]

    monkeypatch.setattr(svc_mod, "SIE_URL", "http://sie")
    monkeypatch.setattr(svc_mod, "SIE_CACHE_FILE", str(cache))
    monkeypatch.setattr(svc_mod, "_embed_with_sie", fake)
    monkeypatch.setattr(svc_mod, "_EMBED_CACHE", {})
    monkeypatch.setattr(svc_mod, "_disk_cache_loaded", False)
    service.find_similar_articles("cafe", 1)
    assert cache.is_file() and calls

    # A new process: empty memory cache, same file.
    monkeypatch.setattr(svc_mod, "_EMBED_CACHE", {})
    monkeypatch.setattr(svc_mod, "_disk_cache_loaded", False)
    calls.clear()
    service.find_similar_articles("cafe", 1)
    assert calls == []  # everything came from disk


# ── Phase 3: semantic categories ──

def _test_rules(monkeypatch):
    from article_receiver import service as svc_mod
    monkeypatch.setitem(svc_mod.CONFIG["categories"], "rules", [
        {"name": "Cafes", "keywords": ["zzz"], "description": "cafe spots"},
        {"name": "Villas", "keywords": ["qqq"], "description": "villa stays"},
    ])


def test_topics_get_a_semantic_category_when_no_keyword_matches(service, monkeypatch):
    _fake_sie(monkeypatch)
    _test_rules(monkeypatch)
    _add_offbrand_topic(sources=1)
    topics = {t["title"].lower(): t for t in json.loads(service.list_pending_topics())}
    cafes = next(t for k, t in topics.items() if "cafe" in k)
    assert (cafes["category"], cafes["category_source"]) == ("Cafes", "sie")
    bjp = topics["bjp dispute"]
    assert (bjp["category"], bjp["category_source"]) == ("Local News", "sie")  # off-brand


def test_keyword_rules_win_over_semantic_categories(service, monkeypatch):
    _fake_sie(monkeypatch)
    topics = json.loads(service.list_pending_topics())
    assert all(t["category_source"] == "keyword" for t in topics)  # every sample topic has a keyword


def test_categories_without_sie_use_keywords_or_default(service, monkeypatch):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    _test_rules(monkeypatch)
    topics = json.loads(service.list_pending_topics())
    assert {t["category"] for t in topics} == {"Guide"}
    assert {t["category_source"] for t in topics} == {"default"}


# ── Phase 4: evaluation ──

LABELS = """labels:
  - {topic: "Goa coffee spots", on_brand: true, covered: false, category: "Food & Nightlife"}
  - {topic: "villas with pools in Vagator", on_brand: true, covered: false, category: "Stays & Villas"}
  - {topic: "BJP dispute", on_brand: false, covered: false, category: "Local News"}
"""


def _labels(tmp_path, monkeypatch, text=LABELS):
    from article_receiver import service as svc_mod
    path = tmp_path / "labels.yaml"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setitem(svc_mod.CONFIG["semantic"], "eval_labels", str(path))


def test_evaluation_without_sie_reports_keyword_only(service, monkeypatch, tmp_path):
    monkeypatch.setattr("article_receiver.service.SIE_URL", "")
    _labels(tmp_path, monkeypatch)
    out = json.loads(service.evaluate_semantic_engine())
    assert out["sie_available"] is False and out["labelled"] == 3
    brand = out["tasks"][0]
    assert brand["keyword"]["total"] == 3 and "sie" not in brand
    assert all("sie" not in item for item in out["items"])


def test_evaluation_with_sie_compares_both_engines(service, monkeypatch, tmp_path):
    _fake_sie(monkeypatch)
    _labels(tmp_path, monkeypatch)
    out = json.loads(service.evaluate_semantic_engine())
    brand, covered, category = out["tasks"]
    assert brand["sie"]["accuracy"] == 1.0  # the fake separates BJP from the travel topics
    assert brand["keyword"]["accuracy"] < 1.0  # "Goa coffee spots" has no tier keyword
    assert [s["value"] for s in brand["sweep"]][0] == 0.1
    assert covered["threshold"]["name"] == "covered_threshold"
    assert {v["name"] for v in category["variants"]} >= {"SIE only"}
    bjp = next(i for i in out["items"] if i["topic"] == "BJP dispute")
    assert bjp["sie"]["on_brand"] is False and bjp["sie"]["category"] == "Local News"


def test_evaluation_needs_a_labels_file(service, monkeypatch, tmp_path):
    from article_receiver import service as svc_mod
    monkeypatch.setitem(svc_mod.CONFIG["semantic"], "eval_labels", str(tmp_path / "missing.yaml"))
    with pytest.raises(ValueError, match="No labels file"):
        service.evaluate_semantic_engine()


def test_bundled_labels_file_is_valid():
    import pathlib, yaml
    from article_receiver.service import CONFIG
    path = pathlib.Path(__file__).resolve().parents[1] / "config" / "eval" / "wayzyy-labels.yaml"
    labels = yaml.safe_load(path.read_text(encoding="utf-8"))["labels"]
    names = {r["name"] for r in CONFIG["categories"]["rules"]}
    assert len(labels) >= 50
    assert all(set(x) == {"topic", "on_brand", "covered", "category"} for x in labels)
    assert all(x["category"] in names for x in labels)
