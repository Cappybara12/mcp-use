import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAAS = ROOT / "config" / "examples" / "saas" / "config.yaml"
WAYZYY = ROOT / "config" / "wayzyy.yaml"


def test_wayzyy_yaml_matches_builtin_defaults():
    """The shipped YAML and the in-code defaults must never drift apart."""
    import sys
    sys.path.insert(0, str(ROOT))
    from article_receiver import service as s

    from_file = s._load_config(WAYZYY)
    builtin = s._load_config(None)
    from_file.pop("_path", None)
    assert from_file == builtin


def test_saas_example_retargets_brand(service_with_config):
    svc = service_with_config(SAAS)
    status = json.loads(svc.get_pipeline_status())
    assert "Acme Analytics" in status["active_brand"]
    assert "Wayzyy" not in status["active_brand"]


def test_saas_example_uses_its_own_sample_data(service_with_config):
    svc = service_with_config(SAAS)
    titles = {t["title"] for t in json.loads(svc.list_pending_topics())}
    assert "Mixpanel alternatives pricing comparison" in titles
    assert not any("Goa" in t for t in titles)


def test_saas_categories_and_suggestion(service_with_config):
    svc = service_with_config(SAAS)
    topics = {t["title"]: t["category"] for t in json.loads(svc.list_pending_topics())}
    assert topics["How to set up event tracking in a React app"] == "Tutorials"
    # "pricing/comparison" is the top tier in the SaaS config
    assert json.loads(svc.suggest_next_article())["topic"] == "Mixpanel alternatives pricing comparison"


def test_saas_style_rules_replace_travel_rules(service_with_config, tmp_path):
    svc = service_with_config(SAAS)
    svc.save_draft("buzz.md", "# T\n\nOur revolutionary tool is a game-changer.\n\n## Why\nIt works.")
    audit = json.loads(svc.run_style_check("buzz.md"))
    assert {"revolutionary", "game-changer"} <= set(audit["ai_cliches_found"])
    # "hidden gem" is only banned in the Wayzyy config
    svc.save_draft("gem.md", "# T\n\nA hidden gem for analytics.\n\n## Why\nIt works.")
    assert json.loads(svc.run_style_check("gem.md"))["ai_cliches_found"] == []


def test_partial_config_falls_back_to_defaults(service_with_config, tmp_path):
    cfg = tmp_path / "partial.yaml"
    cfg.write_text("brand:\n  name: Only Name\n", encoding="utf-8")
    svc = service_with_config(cfg)
    status = json.loads(svc.get_pipeline_status())
    assert status["active_brand"].startswith("Only Name")
    # untouched sections keep the default rules
    svc.save_draft("a.md", "# T\n\nHidden gem here.\n\n## H\nx")
    assert "hidden gem" in json.loads(svc.run_style_check("a.md"))["ai_cliches_found"]


@pytest.mark.parametrize("bad", [
    "categories:\n  rules:\n    - keywords: [x]\n",
    "style:\n  banned_words: not-a-list\n",
    "suggestion:\n  tiers:\n    - [ok]\n    - 5\n",
    "- just\n- a list\n",
])
def test_invalid_config_gives_clear_error(service_with_config, tmp_path, bad):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="Config error"):
        service_with_config(cfg)


def test_missing_config_file_is_an_error(service_with_config, tmp_path):
    with pytest.raises(FileNotFoundError):
        service_with_config(tmp_path / "nope.yaml")
