import json
import os
import stat

import pytest

from article_receiver.studio import nodes, store
from article_receiver.studio.store import StudioError


# ── identifiers and paths ─────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["../x", "a/b", "A", "", "-x", "x" * 41, "a b", "..", ".", "a\x00b", None, 5])
def test_workspace_ids_are_validated(api, bad):
    with pytest.raises(StudioError):
        store.ws_dir(bad)
    with pytest.raises(StudioError):
        api.workspace(bad)


def test_workspace_data_stays_inside_the_data_folder(api, ws, studio_env):
    path = store.ws_dir(ws)
    assert str(path).startswith(str((studio_env / "studio-data").resolve()))


def test_symlinked_workspace_cannot_point_outside(api, studio_env):
    outside = studio_env / "outside"
    outside.mkdir()
    (outside / "config.json").write_text("{}")
    (store.workspaces_dir() / "evil").symlink_to(outside)
    with pytest.raises(StudioError):
        store.ws_dir("evil")


@pytest.mark.parametrize("bad", ["../x", "a/b", "", "x" * 65, "a b"])
def test_pipeline_and_run_ids_are_validated(api, ws, bad):
    with pytest.raises(StudioError):
        api.get_pipeline(ws, bad)
    with pytest.raises(StudioError):
        api.get_run(ws, bad)


def test_workspace_names_become_safe_unique_slugs(api):
    a = api.create_workspace("My Blog!!", "", "", "demo")["id"]
    b = api.create_workspace("My Blog!!", "", "", "demo")["id"]
    assert a == "my-blog" and b != a
    assert api.create_workspace("../../etc", "", "", "demo")["id"] == "etc"


def test_workspace_requires_a_name_and_valid_site_url(api):
    with pytest.raises(StudioError):
        api.create_workspace("  ", "", "", "demo")
    with pytest.raises(StudioError):
        api.create_workspace("X", "javascript:alert(1)", "", "demo")


def test_delete_workspace_removes_everything(api, ws):
    api.set_secret(ws, "main", "openai", "sk-abc12345678")
    api.delete_workspace(ws)
    assert api.list_workspaces() == []


# ── config ────────────────────────────────────────────────────────────────────

def test_config_rejects_unknown_keys_and_bad_values(api, ws):
    for patch in ({"nope": 1}, {"categories": "x"}, {"categories": [""]}, {"site_url": "ftp://x"}, {"voice_prompt": 5}, {"github": {"repo": 5}}):
        with pytest.raises(StudioError):
            api.save_config(ws, json.dumps(patch))


def test_config_merges_nested_settings(api, ws):
    api.save_config(ws, json.dumps({"github": {"repo": "me/site"}}))
    cfg = store.get_config(ws)
    assert cfg["github"]["repo"] == "me/site" and cfg["github"]["base_branch"] == "main"


# ── secrets ───────────────────────────────────────────────────────────────────

def test_secret_file_is_owner_only(api, ws):
    api.set_secret(ws, "main", "openai", "sk-abc12345678")
    mode = stat.S_IMODE(os.stat(store.sub_path(ws, "secrets.json")).st_mode)
    assert mode == 0o600


def test_keys_are_never_returned(api, ws):
    secret = "sk-SUPERSECRET-1234567890"
    listed = api.set_secret(ws, "main", "openai", secret)
    blob = json.dumps([listed, api.workspace(ws), api.catalog()])
    assert secret not in blob
    assert listed[0]["masked"].endswith("7890") and secret[:-4] not in listed[0]["masked"]


@pytest.mark.parametrize("slot,provider,key", [("Bad Slot", "openai", "k" * 12), ("ok", "OPENAI!", "k" * 12), ("ok", "openai", ""),
                                               ("ok", "openai", "two words"), ("ok", "openai", "k" * 5000), ("../x", "openai", "k" * 12)])
def test_invalid_secrets_are_rejected(api, ws, slot, provider, key):
    with pytest.raises(StudioError):
        api.set_secret(ws, slot, provider, key)


def test_key_resolution_order(api, ws, monkeypatch):
    with pytest.raises(StudioError, match="No API key for openai"):
        store.resolve_key(ws, "openai")
    monkeypatch.setenv("STUDIO_KEY_OPENAI", "env-key")
    assert store.resolve_key(ws, "openai") == "env-key"
    api.set_secret(ws, "work", "openai", "workspace-key")
    assert store.resolve_key(ws, "openai") == "workspace-key"           # a saved key beats the environment
    api.set_secret(ws, "other", "openai", "other-key")
    assert store.resolve_key(ws, "openai", "other") == "other-key"      # a named slot is exact
    api.save_config(ws, json.dumps({"default_key_slot": "other"}))
    assert store.resolve_key(ws, "openai") == "other-key"               # the workspace default wins over 'any slot'
    with pytest.raises(StudioError, match="not set"):
        store.resolve_key(ws, "openai", "missing")
    monkeypatch.setenv("STUDIO_KEY_SLOT_MISSING", "ci-key")
    assert store.resolve_key(ws, "openai", "missing") == "ci-key"       # CI can supply a named slot by environment


def test_delete_secret(api, ws):
    api.set_secret(ws, "a", "openai", "k" * 12)
    assert api.delete_secret(ws, "a") == []


# ── pipelines ─────────────────────────────────────────────────────────────────

def _pipeline(nodes_, edges=None, pid="p1"):
    return json.dumps({"id": pid, "name": "P", "nodes": nodes_, "edges": edges or []})


def _node(i, t="topic"):
    return {"id": i, "type": t, "config": {}, "position": {"x": 1, "y": 2}}


def test_valid_pipeline_roundtrips(api, ws):
    saved = api.save_pipeline(ws, _pipeline([_node("a"), _node("b", "keywords")], [{"source": "a", "target": "b"}]))
    assert api.get_pipeline(ws, "p1")["edges"][0]["target"] == "b" and saved["updated_at"]


@pytest.mark.parametrize("payload,match", [
    (_pipeline([_node("a"), _node("a")]), "Duplicate"),
    (_pipeline([_node("a", "nope")]), "Unknown node type"),
    (_pipeline([_node("a")], [{"source": "a", "target": "zzz"}]), "edge"),
    (_pipeline([_node("a")], [{"source": "a", "target": "a"}]), "edge"),
    (_pipeline([_node("a"), _node("b")], [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]), "loop"),
    (_pipeline([_node(f"n{i}") for i in range(61)]), "at most"),
    (_pipeline([_node("../a")]), "Invalid"),
    ('{"id": "p", "nodes": "x"}', "nodes"),
    ("not json", "valid JSON"),
])
def test_invalid_pipelines_are_rejected(api, ws, payload, match):
    with pytest.raises(StudioError, match=match):
        api.save_pipeline(ws, payload)


def test_last_pipeline_cannot_be_deleted(api, ws):
    with pytest.raises(StudioError):
        api.delete_pipeline(ws, "blog-engine")
    api.new_pipeline(ws, "Second", True)
    assert len(api.delete_pipeline(ws, "second")) == 1


def test_every_default_node_type_is_registered():
    for live in (False, True):
        for n in nodes.default_pipeline(live)["nodes"]:
            assert n["type"] in nodes.NODE_TYPES


# ── plan ──────────────────────────────────────────────────────────────────────

def test_plan_items_validate_and_normalise_dates(api, ws):
    item = json.loads(json.dumps(api.save_plan_item(ws, json.dumps({"title": "A post", "scheduled_for": "2026-12-01T09:00:00+02:00"}))))
    assert item["scheduled_for"] == "2026-12-01T07:00:00+00:00" and item["status"] == "planned"
    assert api.save_plan_item(ws, json.dumps({"title": "Idea only"}))["status"] == "idea"


@pytest.mark.parametrize("bad", [{"title": ""}, {"title": "x", "status": "weird"}, {"title": "x", "scheduled_for": "tomorrow"},
                                 {"title": "x", "scheduled_for": 5}, {"id": "../x", "title": "x"}, {"title": "x", "pipeline_id": "../p"}])
def test_bad_plan_items_are_rejected(api, ws, bad):
    with pytest.raises(StudioError):
        api.save_plan_item(ws, json.dumps(bad))


def test_plan_update_and_delete(api, ws):
    first = api.save_plan_item(ws, json.dumps({"title": "One", "category": "Guides"}))
    api.save_plan_item(ws, json.dumps({"id": first["id"], "title": "One v2"}))
    plan = api.list_plan(ws)
    assert len(plan) == 1 and plan[0]["title"] == "One v2" and plan[0]["category"] == "Guides"
    assert api.delete_plan_item(ws, first["id"]) == []


# ── rulebook ──────────────────────────────────────────────────────────────────

def test_rulebook_validation(api, ws):
    good = {"rules": [{"id": "r1", "kind": "note", "text": "Be clear", "params": {}}]}
    assert api.save_rulebook(ws, json.dumps(good))["rules"][0]["enabled"] is True
    for bad in ({"rules": "x"}, {"rules": [{"id": "r1", "kind": "evil", "text": "x"}]}, {"rules": [{"id": "r1", "kind": "note", "text": ""}]},
                {"rules": [{"id": "r1", "kind": "note", "text": "x"}, {"id": "r1", "kind": "note", "text": "y"}]},
                {"rules": [{"id": "r1", "kind": "note", "text": "x", "params": {"a": {"nested": 1}}}]},
                {"rules": [{"id": f"r{i}", "kind": "note", "text": "x"} for i in range(61)]}):
        with pytest.raises(StudioError):
            api.save_rulebook(ws, json.dumps(bad))


def test_custom_rules(api, ws):
    api.add_custom_rule(ws, "Never say synergy", "banned_phrases", "synergy, game-changer")
    rule = store.get_rulebook(ws)["rules"][-1]
    assert rule["source"] == "custom" and rule["params"]["phrases"] == ["synergy", "game-changer"]


def test_ideas_are_deduplicated(api, ws):
    api.add_idea(ws, "Same idea", "kw", "")
    api.add_idea(ws, "same IDEA", "kw", "")
    assert len(api.list_ideas(ws)) == 1
