"""The editorial quality gates and the way they connect to the pipeline."""
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAAS = ROOT / "config" / "examples" / "saas" / "config.yaml"

PARAGRAPH = (
    "Check the neighbourhood before you book, because the same rental can feel very different "
    "from one lane to the next. Ask the host for a recent photo of the street and read the "
    "reviews that mention noise, parking and walking distance to food. "
)


def long_draft(extra="", words=950):
    body = (PARAGRAPH * (words // len(PARAGRAPH.split()) + 1)).strip()
    return (
        "# Choosing a stay in Goa\n\nIntro for travellers planning a trip to Goa.\n\n"
        "## Where to look\n" + body + "\n\n## FAQ\nIs it busy in July? Less than in December.\n\n"
        "Source: https://example.com/guide\nPhoto credit: Pexels.\n" + extra
    )


def audit(svc, name, text):
    svc.save_draft(name, text)
    return json.loads(svc.run_style_check(name))


def test_compliant_draft_scores_100_with_no_advice(service):
    result = audit(service, "ok.md", long_draft())
    assert result["brand_score"] == 100
    assert result["recommendations"] == []


@pytest.mark.parametrize("remove,needle", [
    ("https://example.com/guide", "source links"),
    ("## FAQ", "FAQ"),
    ("Photo credit: Pexels.", "image credit"),
])
def test_each_missing_gate_costs_points_and_says_why(service, remove, needle):
    text = long_draft().replace(remove, "removed")
    result = audit(service, "gap.md", text)
    assert result["brand_score"] < 100
    assert any(needle.lower() in r.lower() for r in result["recommendations"])


def test_every_lost_point_has_a_recommendation(service):
    for text in [long_draft(words=300), long_draft().replace("https://example.com/guide", ""),
                 long_draft("The house is being sold and was cleaned and is painted.")]:
        result = audit(service, "any.md", text)
        if result["brand_score"] < 100:
            assert result["recommendations"], result


def test_destination_keyword_is_not_treated_as_primary_keyword(service):
    # "Goa" appears far more than the keyword limit, but it is the destination, not the primary keyword.
    result = audit(service, "goa.md", long_draft("Goa " * 40))
    assert not any("Reduce uses" in r for r in result["recommendations"])


def test_primary_keyword_from_front_matter_is_enforced(service):
    text = "---\nprimary_keyword: villa pool\n---\n" + long_draft("villa pool " * 12)
    result = audit(service, "kw.md", text)
    assert any("villa pool" in r and "Reduce uses" in r for r in result["recommendations"])


def test_image_attribution_can_be_switched_off(service_with_config, tmp_path):
    svc = service_with_config(SAAS)  # the SaaS config does not require image credit
    text = long_draft().replace("Photo credit: Pexels.", "").replace("Goa", "analytics").replace("## FAQ", "## FAQ\n## examples")
    result = json.loads((svc.save_draft("s.md", text), svc.run_style_check("s.md"))[1])
    assert not any("image credit" in r for r in result["recommendations"])


@pytest.mark.parametrize("bad", [
    "editorial:\n  minimum_words: many\n",
    "editorial:\n  minimum_words: -5\n",
    "editorial:\n  required_sections: FAQ\n",
    "editorial:\n  require_sources: maybe\n",
])
def test_invalid_editorial_config_is_rejected(service_with_config, tmp_path, bad):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="Config error"):
        service_with_config(cfg)


def test_pipeline_receives_the_configured_niche_not_wayzyys():
    """When this folder sits next to the real pipeline, a retargeted config must reach its prompts."""
    pipeline_root = ROOT.parent.parent  # the folder that holds agent/ in the mcp-use layout
    if not (pipeline_root / "agent" / "config.py").is_file():
        pytest.skip("article pipeline (agent/) is not next to this folder")
    import os
    sys.path.insert(0, str(pipeline_root))
    old = os.environ.get("PIPELINE_CONFIG")
    os.environ["PIPELINE_CONFIG"] = str(SAAS)
    try:
        import agent.config as pipeline_config
        importlib.reload(pipeline_config)
        contract = pipeline_config.editorial_contract()
    finally:
        if old is None:
            os.environ.pop("PIPELINE_CONFIG")
        else:
            os.environ["PIPELINE_CONFIG"] = old
        importlib.reload(pipeline_config)
        sys.path.remove(str(pipeline_root))
    assert "Acme Analytics" in contract
    assert "Goa" not in contract


def test_unknown_publisher_gives_a_clear_error(tmp_path, monkeypatch):
    (tmp_path / "writer" / "agent").mkdir(parents=True)  # makes the receiver think a pipeline is attached
    monkeypatch.setenv("WAYZYY_WRITER_DIR", str(tmp_path / "writer"))
    monkeypatch.setenv("WAYZYY_SCANNER_DIR", str(tmp_path / "none"))
    monkeypatch.setenv("WAYZYY_DRAFTS_DIR", str(tmp_path / "drafts"))
    monkeypatch.setenv("PUBLISHER_MODULE", "no_such_publisher_module")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    (tmp_path / "drafts").mkdir()
    for mod in [m for m in sys.modules if m.startswith("article_receiver")]:
        del sys.modules[mod]
    from article_receiver.service import ArticlePipelineService
    with pytest.raises(RuntimeError, match="Could not load publisher"):
        ArticlePipelineService().push_to_github("x.md")
