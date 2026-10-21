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


def test_style_check_clean_draft_scores_100(service):
    audit = json.loads(service.run_style_check("sample-assagao"))
    assert audit["brand_score"] == 100
    assert "Includes Pexels attribution" in audit["passed_checks"]


def test_missing_draft_raises(service):
    with pytest.raises(ValueError):
        service.get_draft("does-not-exist")


def test_save_draft_cannot_escape_drafts_dir(service, tmp_path):
    result = json.loads(service.save_draft("../../escape.md", "x"))
    assert result["filename"] == "escape.md"
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
